from trainingpeaks_delivery import (
    trainingpeaks_delivery_markdown,
    trainingpeaks_delivery_steps,
)


def test_steps_are_ordered_and_omit_account_ids():
    steps = trainingpeaks_delivery_steps(
        plan_start='2026-08-17', race_week_monday='2026-09-14')
    assert len(steps) == 6
    assert '2026-08-17' in steps[3]
    assert '2026-09-14' in steps[3]
    joined = ' '.join(steps)
    assert 'cs_live' not in joined
    assert '@' not in joined


def test_markdown_names_the_manual_path():
    md = trainingpeaks_delivery_markdown()
    assert md.startswith('## TrainingPeaks delivery')
    assert 'Automated calendar apply is not live' in md
    assert 'full package' in md
