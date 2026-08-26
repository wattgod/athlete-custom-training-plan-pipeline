# Sol avatar shadow judge

Status: manual, synthetic-only, advisory evaluation.

This pilot sends generated `avatar-*` plans through GPT-5.6 Sol using Vercel AI
Gateway. It does not replace the daily Claude judge, modify the improvement
backlog, alter a plan, or participate in paid-athlete fulfillment.

## Privacy and spend controls

- The evaluator rejects any package whose directory is not `avatar-*` or whose
  profile email does not end in `@synthetic.local` before networking.
- The dedicated `motoren-sol-avatar-shadow` key has a $50 non-refreshing quota,
  expires after 90 days, and alerts at 50/75/100%.
- Endure uses a separate $50 pilot key; combined key exposure is $100.
- Auto top-up is off.
- Each request has a conservative $1 local ceiling and records response token
  usage plus estimated spend.
- The GitHub workflow is manual, accepts at most five avatars, writes no repo
  content, and retains only its advisory report for 14 days.

## Run

Use **Actions → Sol Avatar Shadow Judge → Run workflow**. Start with two
avatars. The repository secret `AI_GATEWAY_API_KEY` is already scoped to this
pilot key.

For a local dry run without Gateway access:

```bash
python3 athletes/scripts/daily_avatar_run.py \
  --count 1 --seed local-check --judge none
```
