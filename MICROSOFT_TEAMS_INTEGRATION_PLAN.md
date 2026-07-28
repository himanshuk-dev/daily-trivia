# Microsoft Teams Integration Plan

Branch: `feature/microsoft-teams-integration`

## Goal

Connect each Daily Trivia team to one Microsoft Teams team/channel so that published trivia appears in the channel, approved members can answer from Teams, and the website immediately reflects the same submission and result state.

Daily Trivia remains the source of truth for users, teams, trivia, deadlines, answers, scoring, trophies, and leaderboards. Teams is an additional client.

## Recommended architecture

Use a Microsoft Teams app with a bot and Adaptive Cards, backed by the existing Django API. The card contains the question and answer actions. Each action calls Daily Trivia, which validates identity, membership, deadline, and choice before saving the answer.

Microsoft Graph can post a channel message with `POST /teams/{team-id}/channels/{channel-id}/messages`, but ordinary posting uses delegated `ChannelMessage.Send`; application permissions are limited for this scenario. Therefore, use a Teams bot/app identity for unattended production publishing and obtain SSC tenant consent. See the [Graph channel-message API](https://learn.microsoft.com/en-us/graph/api/channel-post-messages?view=graph-rest-1.0).

Use Teams change notifications only if we later need to monitor channel lifecycle or messages. They require subscriptions, renewal, and additional permissions; they should not be the primary answer path. See [Teams change notifications](https://learn.microsoft.com/en-us/graph/teams-changenotifications-chatmessage).

```text
Master publishes -> Django API -> Teams bot -> channel card
                                      |
Member selects answer -> bot callback -> Django answer service -> website
```

## Phase 0 — Decisions and approvals

1. Confirm SSC approval for a Teams app/bot in the SSC Microsoft Entra tenant.
2. Start with standard channels; defer private/shared channels until permissions are proven.
3. Enforce one-to-one mapping: one Daily Trivia team to one Teams team/channel.
4. Keep the existing SSC-only `@ssc-spc.gc.ca` restriction.
5. Confirm that only approved Daily Trivia members may answer.
6. Use non-sensitive test trivia until hosting and security approvals are complete.

## Phase 1 — Microsoft identity and Teams app

1. Register the application in the SSC Microsoft Entra tenant.
2. Create the Teams app manifest, bot ID, bot endpoint, and icons.
3. Configure redirect/callback URLs and the tenant ID.
4. Request the minimum permissions required by the selected bot/Graph flow.
5. Obtain SSC admin consent.
6. Store client secrets/certificates only in Render secrets or a managed secret store.

## Phase 2 — Channel connection model

Add a `TeamsChannelConnection` model related to `Team`:

- Daily Trivia team ID
- Microsoft team ID and channel ID
- display names
- status (`pending`, `active`, `disabled`, `error`)
- connected by, timestamps, last success, and last error

Add a unique constraint for the Microsoft team/channel pair. Do not delete the connection when trivia history is deleted.

Add platform-admin/team-admin controls to connect, verify, test, disconnect, and view delivery status. The first version may accept team/channel IDs manually; a channel picker can follow later.

## Phase 3 — Publish trivia to Teams

When a session becomes `LIVE` for either manual or AI trivia:

1. Find the active channel connection.
2. Create a `TeamsTriviaMessage` delivery record.
3. Build an Adaptive Card containing title, topic, question, choices, close time, and a website link.
4. Post it through the Teams bot.
5. Save the Teams message ID and delivery status.
6. Retry transient failures with bounded backoff.
7. Use an idempotency key such as `session:{id}:channel:{id}` to prevent duplicate posts.
8. Keep website trivia live if Teams delivery fails, but show the master/admin the error.

## Phase 4 — Accept answers from Teams

Create a callback such as:

```text
POST /api/integrations/microsoft-teams/card-actions/
```

For each card submission:

1. Validate the bot request signature/token.
2. Read the trusted Microsoft Entra tenant and object ID.
3. Map the identity to an SSC Daily Trivia user; never trust typed email or username data.
4. Confirm approved membership in the mapped Daily Trivia team.
5. Confirm the session is live and `close_at` has not passed.
6. Confirm the selected choice belongs to the question.
7. Call the same domain answer service used by the website.
8. Enforce one answer per user/question and make repeated clicks idempotent.
9. Return an updated card showing “Answer submitted” and the closing time.

## Phase 5 — Synchronize website and Teams

- Store Teams and website answers in the same `UserAnswer` table.
- Add an answer source (`website` or `microsoft_teams`) or an audit event if needed.
- Reuse existing evaluation, trophy, leaderboard, and notification logic.
- Do not allow a later website answer to overwrite an existing Teams answer.
- After evaluation, update the card when supported or post a concise result reply with a website link.
- Continue using the website’s refresh/polling behavior so Teams submissions appear without a full-page reload.

## Phase 6 — Backend and frontend implementation order

1. Add models, migration, settings, and feature flag `MICROSOFT_TEAMS_ENABLED`.
2. Add a Teams integration service and mocked client.
3. Add channel connection APIs and admin UI.
4. Add outbound card publishing for manual and AI sessions.
5. Add bot callback and secure identity mapping.
6. Refactor website and Teams submissions through one answer service.
7. Add delivery status, retries, correlation IDs, and admin error display.
8. Add subscription renewal only if Graph change notifications become necessary.

## Testing plan

### Automated backend tests

- Only authorized admins can connect/disconnect a channel.
- A channel connection is unique and cannot be duplicated.
- Manual and AI publication each create one delivery record.
- Retries do not duplicate a Teams message.
- Invalid bot signatures, tenants, users, teams, and choices are rejected.
- Pending, closed, or expired trivia rejects Teams answers.
- Duplicate card submissions are idempotent.
- Teams answers appear in normal submissions, evaluation, trophies, and leaderboards.
- Existing website answer behavior remains unchanged.

### Acceptance test

1. Connect one test Daily Trivia team to one standard Teams channel.
2. Publish a manual question and confirm its card appears.
3. Answer in Teams and confirm the website shows the submission.
4. Try a second answer and confirm it is rejected/idempotent.
5. Answer from the website as another member.
6. Close/evaluate and confirm both views show the result.
7. Test an expired card, an unapproved user, and a disconnected channel.

Use a mocked Teams client in automated tests and a dedicated SSC test channel for end-to-end testing. Never run automated tests against a production channel.

## Deployment and operations

- Add placeholders to `.env.example` and deployment documentation; never commit credentials.
- Store tenant ID, client ID, bot credentials, signing/encryption settings, and endpoint configuration as production secrets.
- Log session ID, Daily Trivia team ID, Teams channel ID, delivery status, and correlation ID; never log tokens.
- Add a kill switch so the website remains usable if Teams is unavailable.
- Monitor delivery failures and renew subscriptions if subscriptions are introduced.
- Pilot with one team before enabling the integration for all teams.

## Definition of done

- An authorized admin connects one Teams channel to a Daily Trivia team.
- Manual and AI trivia publish to the mapped channel.
- An approved SSC member answers once from Teams.
- The answer appears on the website without manual entry.
- Teams and website enforce identical membership, deadline, scoring, and result rules.
- Failures are visible and retryable without duplicate messages.
- The integration can be disabled without affecting the core website.
