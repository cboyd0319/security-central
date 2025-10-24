# Secret Rotation Schedule

## GitHub PAT (GH_PAT)
- **Frequency:** Every 90 days
- **Owner:** @cboyd0319
- **Process:**
  1. Generate new fine-grained PAT with same permissions
  2. Test in dev workflow: `gh workflow run test-auth.yml`
  3. Update secret: `gh secret set GH_PAT`
  4. Verify all workflows still work
  5. Delete old token from GitHub
  6. Update password manager

**Next Rotation:** 2025-01-24 (set calendar reminder)

## Slack Webhooks
- **Frequency:** Only if compromised
- **Owner:** @cboyd0319
- **Process:**
  1. Regenerate webhook in Slack admin
  2. Update all secrets: `gh secret set SLACK_WEBHOOK`
  3. Test: `make test-slack`

## OpenAI API Key (if used)
- **Frequency:** Every 180 days
- **Cost Control:** Set usage limit to $50/month
- **Monitor:** https://platform.openai.com/usage
