# Privacy Policy — Claude Vault

**Extension:** Claude Vault - Search, Bookmark & Export  
**Developer:** Jamie Cole (independent developer, United Kingdom)  
**Last updated:** 1 March 2026

---

## Summary

Claude Vault does not collect, transmit, or share any personal data. Everything the extension does happens entirely on your device.

---

## What data the extension handles

Claude Vault reads your Claude.ai conversation list (titles, UUIDs, timestamps) when you visit claude.ai. This data is:

- **Stored locally only** — saved to `chrome.storage.local` on your device
- **Never sent anywhere** — no servers, no analytics, no third parties receive this data
- **Only used to power features you use** — search, bookmarks, and export

When you export a conversation, the extension reads the page content and creates a Markdown file that downloads directly to your computer. That file never passes through any external server.

---

## Data storage

| What | Where | Why |
|------|-------|-----|
| Conversation index (titles + UUIDs) | `chrome.storage.local` | Powers the search feature |
| Bookmarked conversation IDs | `chrome.storage.local` | Powers the bookmarks feature |
| Extension settings/preferences | `chrome.storage.local` | Remembers your settings |

All data lives in your browser's local storage. Uninstalling the extension removes it.

---

## What the extension does NOT do

- Does not collect names, emails, IP addresses, or any personally identifiable information
- Does not use cookies or tracking pixels
- Does not include analytics (no Google Analytics, Mixpanel, Sentry, or similar)
- Does not make any network requests except to `claude.ai` itself (the site you're already visiting)
- Does not sell or share any data with any third party

---

## Host permissions

The extension requests access to `https://claude.ai/*`. This is the only site it operates on. It intercepts the conversation list API response from Claude's own servers so it can build a local search index. No data from this interception leaves your device.

---

## Changes to this policy

If anything material changes, the updated policy will be published here and noted in the extension's changelog.

---

## Contact

Questions? Email: clawgenesis@gmail.com
