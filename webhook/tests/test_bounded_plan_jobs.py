"""Concurrency and capacity checks for durable paid-order generation jobs."""

import json
import multiprocessing
import os
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _claim_in_process(jobs_dir, order_id, gate, results):
    import app
    app.JOBS_DIR = jobs_dir
    gate.wait()
    claimed = app._claim_plan_job(order_id)
    results.put(bool(claimed))


def _sweep_in_process(jobs_dir, deliveries_dir, gate, results):
    import app
    app.JOBS_DIR = jobs_dir
    app.DELIVERIES_DIR = deliveries_dir
    gate.wait()
    with patch.object(app, '_dispatch_queued_jobs'), \
         patch.dict(os.environ, {'SYNC_PIPELINE': ''}):
        results.put(app.sweep_stuck_jobs())


def test_two_processes_claim_one_order_once():
    import app
    with tempfile.TemporaryDirectory() as root:
        with patch.object(app, 'JOBS_DIR', root):
            app._write_job({'order_id': 'cs_claim_once', 'athlete_id': 'one',
                            'status': 'queued', 'attempts': 1})
        ctx = multiprocessing.get_context('fork')
        gate = ctx.Event()
        results = ctx.Queue()
        processes = [ctx.Process(target=_claim_in_process,
                                 args=(root, 'cs_claim_once', gate, results))
                     for _ in range(2)]
        for process in processes:
            process.start()
        gate.set()
        values = [results.get(timeout=5) for _ in processes]
        for process in processes:
            process.join(timeout=5)
            assert process.exitcode == 0
        assert sorted(values) == [False, True]
        record = json.loads((Path(root) / 'orders' / 'cs_claim_once.json').read_text())
        assert record['status'] == 'running'
        assert record['attempts'] == 1


def test_two_process_sweepers_requeue_one_expired_lease_once():
    import app
    with tempfile.TemporaryDirectory() as root:
        jobs_dir = str(Path(root) / 'jobs')
        with patch.object(app, 'JOBS_DIR', jobs_dir):
            app._write_job({'order_id': 'cs_expired', 'athlete_id': 'one',
                            'status': 'running', 'attempts': 1,
                            'max_attempts': 2,
                            'lease_expires_at': (datetime.now() - timedelta(minutes=1)).isoformat()})
        ctx = multiprocessing.get_context('fork')
        gate = ctx.Event()
        results = ctx.Queue()
        processes = [ctx.Process(target=_sweep_in_process,
                                 args=(jobs_dir, str(Path(root) / 'deliveries'), gate, results))
                     for _ in range(2)]
        for process in processes:
            process.start()
        gate.set()
        stats = [results.get(timeout=5) for _ in processes]
        for process in processes:
            process.join(timeout=5)
            assert process.exitcode == 0
        record = json.loads((Path(jobs_dir) / 'orders' / 'cs_expired.json').read_text())
        assert sum(item['retried'] for item in stats) == 1
        assert record['attempts'] == 2
        assert record['status'] == 'queued'


def test_restart_with_sealed_release_skips_generation_and_notice():
    import app
    with tempfile.TemporaryDirectory() as root:
        order_root = Path(root) / 'deliveries' / 'orders' / 'cs_recover'
        order_root.mkdir(parents=True)
        (order_root / 'fulfillment_status.json').write_text('{}')
        with patch.object(app, 'JOBS_DIR', str(Path(root) / 'jobs')), \
             patch.object(app, 'DELIVERIES_DIR', str(Path(root) / 'deliveries')), \
             patch.object(app, 'load_fulfillment_state', return_value={
                 'order_id': 'cs_recover', 'model_seal': 'sealed',
                 'generation_revision': 1}), \
             patch.object(app, 'verify_release_manifest'), \
             patch.object(app, '_execute_plan_job') as generation, \
             patch.object(app, '_notify_new_order') as notify, \
             patch.object(app, '_dispatch_queued_jobs'):
            app._write_job({'order_id': 'cs_recover', 'athlete_id': 'one',
                            'status': 'queued', 'attempts': 2,
                            'notification_attempted_at': datetime.now().isoformat()})
            assert app._job_slots.acquire(blocking=False)
            app._run_claimed_job('cs_recover')
            record = app._read_job('cs_recover')
        assert record['status'] == 'succeeded'
        assert record['recovered_from_release'] is True
        generation.assert_not_called()
        notify.assert_not_called()


def test_restart_with_unsealed_state_stops_and_alerts_coach():
    import app
    with tempfile.TemporaryDirectory() as root:
        order_root = Path(root) / 'deliveries' / 'orders' / 'cs_partial'
        order_root.mkdir(parents=True)
        (order_root / 'fulfillment_status.json').write_text('{}')
        with patch.object(app, 'JOBS_DIR', str(Path(root) / 'jobs')), \
             patch.object(app, 'DELIVERIES_DIR', str(Path(root) / 'deliveries')), \
             patch.object(app, 'load_fulfillment_state', return_value={
                 'order_id': 'cs_partial', 'generation_revision': 1}), \
             patch.object(app, '_execute_plan_job') as generation, \
             patch.object(app, '_notify_new_order') as notify, \
             patch.object(app, '_dispatch_queued_jobs'):
            app._write_job({'order_id': 'cs_partial', 'athlete_id': 'one',
                            'status': 'queued', 'attempts': 2})
            assert app._job_slots.acquire(blocking=False)
            app._run_claimed_job('cs_partial')
            record = app._read_job('cs_partial')
        assert record['status'] == 'failed'
        generation.assert_not_called()
        notify.assert_called_once()
        assert notify.call_args.args[0] == 'training_plan_FAILED'


def test_recovery_notice_timeout_does_not_send_failure_notice():
    import app
    with tempfile.TemporaryDirectory() as root:
        order_root = Path(root) / 'deliveries' / 'orders' / 'cs_notice_timeout'
        order_root.mkdir(parents=True)
        (order_root / 'fulfillment_status.json').write_text('{}')
        with patch.object(app, 'JOBS_DIR', str(Path(root) / 'jobs')), \
             patch.object(app, 'DELIVERIES_DIR', str(Path(root) / 'deliveries')), \
             patch.object(app, 'load_fulfillment_state', return_value={
                 'order_id': 'cs_notice_timeout', 'model_seal': 'sealed',
                 'generation_revision': 1, 'status': 'GENERATED'}), \
             patch.object(app, 'verify_release_manifest'), \
             patch.object(app, '_build_plan_notification_details', return_value={}), \
             patch.object(app, '_generate_review_token', return_value='token'), \
             patch.object(app, '_notify_new_order', side_effect=TimeoutError('ambiguous')) as notify, \
             patch.object(app, '_dispatch_queued_jobs'):
            app._write_job({'order_id': 'cs_notice_timeout', 'athlete_id': 'one',
                            'status': 'queued', 'attempts': 2,
                            'order_data': {'order_id': 'cs_notice_timeout', 'athlete_id': 'one'}})
            assert app._job_slots.acquire(blocking=False)
            app._run_claimed_job('cs_notice_timeout')
            record = app._read_job('cs_notice_timeout')
        assert record['status'] == 'failed'
        assert record['notification_attempted_at']
        notify.assert_called_once()
        assert notify.call_args.args[0] == 'training_plan'


def test_ten_synthetic_orders_drain_with_bounded_workers():
    import app
    with tempfile.TemporaryDirectory() as root:
        active = 0
        peak = 0
        completed = []
        guard = threading.Lock()

        def fake_execute(job, intake_data=None):
            nonlocal active, peak
            with guard:
                active += 1
                peak = max(peak, active)
            time.sleep(0.025)
            app._update_job(job['order_id'], status='succeeded')
            with guard:
                active -= 1
                completed.append(job['order_id'])

        start = time.monotonic()
        with patch.object(app, 'JOBS_DIR', root), \
             patch.object(app, 'DELIVERIES_DIR', str(Path(root) / 'deliveries')), \
             patch.object(app, '_execute_plan_job', side_effect=fake_execute), \
             patch.dict(os.environ, {'SYNC_PIPELINE': ''}):
            for n in range(10):
                app._spawn_plan_job({'order_id': f'cs_burst_{n}',
                                     'athlete_id': f'rider_{n}'})
            deadline = time.monotonic() + 5
            while len(completed) < 10 and time.monotonic() < deadline:
                time.sleep(0.01)
            elapsed = time.monotonic() - start
            records = [app._read_job(f'cs_burst_{n}') for n in range(10)]

        assert len(completed) == len(set(completed)) == 10
        assert all(record['status'] == 'succeeded' for record in records)
        assert peak <= app.JOB_WORKERS_PER_PROCESS
        assert elapsed < 5
        print(f'synthetic drain: 10 jobs in {elapsed:.3f}s, peak active={peak}')


def test_ambiguous_success_notice_never_sends_contradictory_failure_notice():
    import app
    with tempfile.TemporaryDirectory() as root, \
         patch.object(app, 'JOBS_DIR', root), \
         patch.object(app, 'run_pipeline', return_value={
             'success': True, 'stdout': '', 'stderr': '', 'artifact_dir': root}), \
         patch.object(app, 'persist_deliverables', return_value={
             'state': {'status': 'GENERATED', 'blocking_issues': [],
                       'required_confirmations': []}}), \
         patch.object(app, 'log_order'), \
         patch.object(app, '_build_plan_notification_details', return_value={}), \
         patch.object(app, '_generate_review_token', return_value='review-token'), \
         patch.object(app, '_notify_new_order', side_effect=TimeoutError('ambiguous send')) as notify:
        job = {'order_id': 'cs_ambiguous_notice', 'athlete_id': 'one',
               'status': 'queued', 'attempts': 1,
               'order_data': {'order_id': 'cs_ambiguous_notice', 'athlete_id': 'one'}}
        app._write_job(job)
        result = app._execute_plan_job(job)
        record = app._read_job(job['order_id'])
    assert result['success'] is False
    assert record['status'] == 'failed'
    assert record['notification_attempted_at']
    notify.assert_called_once()
    assert notify.call_args.args[0] == 'training_plan'
