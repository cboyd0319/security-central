## 🚨 EMERGENCY: Secret Compromised

If any secret is compromised:

### IMMEDIATE (< 5 minutes)
1. **Revoke the secret:**
   - GitHub PAT: https://github.com/settings/tokens → Delete
   - Slack webhook: Slack admin → Regenerate
   - OpenAI key: https://platform.openai.com/api-keys → Revoke

2. **Disable Security Central workflows:**
```bash
   gh workflow disable orchestrator.yml --repo cboyd0319/security-central
   gh workflow disable dependency-updates.yml --repo cboyd0319/security-central
```

3. **Check for unauthorized access:**
```bash
   gh api /repos/cboyd0319/security-central/events | jq '.[] | select(.type == "PushEvent")'
```

### SHORT-TERM (< 1 hour)
4. **Investigate scope:**
   - Check GitHub audit log: https://github.com/settings/security-log
   - Review recent commits: `git log --since="1 hour ago" --all`
   - Check Slack for unauthorized messages

5. **Rotate all secrets:**
```bash
   ./setup-secrets.sh
```

6. **Re-enable workflows:**
```bash
   gh workflow enable orchestrator.yml --repo cboyd0319/security-central
```

### LONG-TERM (< 24 hours)
7. **Root cause analysis:**
   - How was secret exposed? (commit, logs, etc.)
   - Update `.gitignore` if needed
   - Add pre-commit hooks to prevent recurrence

8. **Notify stakeholders:**
   - Post in #security-incidents
   - Update security advisory if public repos affected

9. **Improve controls:**
   - Enable 2FA on all accounts
   - Review repository collaborators
   - Audit workflow permissions