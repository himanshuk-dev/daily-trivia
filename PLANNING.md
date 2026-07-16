# Daily Trivia Planning Doc

## Product Goal
Build a trivia app where users create usernames, a manually selected master chooses a topic every two weeks, AI generates trivia for that topic, and correct answers earn digital trophies.

## Core Roles
- User: creates a username, joins trivia sessions, answers questions, and collects trophies.
- Master: owns the biweekly trivia cycle, is selected manually, picks the topic, reviews AI-generated trivia, publishes the session, and evaluates answers.
- AI: generates trivia content from the master-selected topic.
- System: stores sessions, answers, trophies, and history.

## Main User Flow
1. A user signs up with a unique username.
2. The current master is chosen manually for the two-week cycle.
3. The master chooses the topic for that cycle.
4. AI generates draft trivia based on the topic.
5. The master reviews, edits, and publishes the trivia.
6. The trivia goes live and users submit answers.
7. The master evaluates submitted answers after the session closes.
8. Each user with a correct answer receives 1 digital trophy.

## MVP Scope
- Username creation and login/session identity.
- Master-only tools for topic selection and trivia publishing.
- AI trivia generation from a topic prompt.
- Trivia live window and user answer submission.
- Answer review and trophy awarding.
- Basic leaderboard or trophy count display.

## Suggested Data Model
- User: id, username, createdAt.
- MasterCycle: id, masterUserId, topic, startDate, endDate, status.
- TriviaSession: id, masterCycleId, title, topic, status, publishAt, closeAt.
- TriviaQuestion: id, triviaSessionId, prompt, choices, correctAnswer, explanation.
- UserAnswer: id, triviaSessionId, userId, answer, submittedAt, isCorrect, evaluatedAt.
- TrophyAward: id, userId, triviaSessionId, awardedAt, reason.

## Technical Design
- Frontend: simple web app for signup, trivia participation, and trophy viewing.
- Backend API: handles users, cycles, trivia sessions, answers, and awards.
- Database: persistent store for users, questions, answers, and trophies.
- AI service: generates structured trivia drafts from the selected topic.
- Admin/master UI: review and publish workflow.

## Confirmed Decisions
- Questions are multiple-choice.
- The master is chosen manually.
- Every user with a correct answer receives a trophy.
- The app includes a public leaderboard.
- Users register with a first name, last name, unique username, and unique email address.
- Authentication uses short-lived email one-time codes instead of passwords.
- Authenticated identity must be enforced by the backend; a user cannot use another username.
- Users can log in, log out, and access a personal account and team-management area.
- The platform has a separate administration dashboard.
- `himanshu.kumar@ssc-spc.gc.ca` is the initial platform administrator and can appoint other platform administrators.
- The application supports multiple persistent teams, each with isolated memberships, trivia cycles, answers, trophies, and leaderboards.
- Users join teams with invite codes. A team can either admit them immediately or require a team administrator's approval.
- A trivia master is assigned for a specific team cycle.
- Masters schedule a different topic for each day of a two-week sprint and can generate one AI question from that day’s topic for a configurable answer window.

## Authentication and Authorization
- Registration collects first name, last name, username, and email, then sends a time-limited one-time code to that email.
- Successful code verification activates the account and creates an authenticated application session.
- Login requests a new one-time code for an existing email address.
- Logout invalidates the active application session.
- Client-provided usernames or user IDs are never sufficient authorization; protected actions use the authenticated identity.
- Development sends codes through Django's console email backend. Production email delivery is configured through environment variables.

## Role Model
- Platform Admin: manages platform users, teams, and other platform admins.
- Team Admin: is assigned per team, manages that team's settings, invite policy, membership requests, and members, can directly add active users, and can assign themselves or another approved member as cycle master.
- Master: creates, reviews, and publishes trivia for an assigned team cycle.
- Member: participates in trivia for approved team memberships.

## Team and Session Model
- Team: id, name, slug, inviteCode, approvalRequired, createdBy, createdAt.
- TeamMembership: id, teamId, userId, role, status, joinedAt, approvedAt.
- MasterCycle belongs to one team and identifies that cycle's master.
- TriviaSession, questions, answers, trophies, history, and leaderboard are scoped through the team cycle.
- Pending memberships cannot access or answer team trivia until approved.

## Application Areas
- Registration, login-code verification, and logout.
- User dashboard for profile, memberships, invitations, and available trivia.
- Team administration for invite codes, members, and approval requests.
- Team creation includes selecting an initial approved team administrator.
- Master trivia builder for manual questions, AI drafts, editing, and publishing.
- Platform administration dashboard for users, teams, and administrator roles.

## Key Rules
- Usernames must be unique.
- Only the active master can create or publish trivia for the current cycle.
- Requesting an AI daily challenge is the master's approval to publish the generated question immediately.
- Trophy awards should be immutable once granted.
- Every award should be tied to a specific trivia session.

## Delivery Plan
### Phase 1
- Email-code signup, login, logout, and authenticated identity.
- Initial platform administrator bootstrap.
- Master cycle setup.
- AI trivia generation.
- Publish and answer flow.
- Trophy awarding.

### Phase 2
- Teams, invite codes, and optional membership approval.
- User and team-management dashboards.
- Platform administrator management.
- Leaderboards.
- Trivia history.
- Master review tools.
- Notifications for new live trivia.

### Phase 3
- Better AI validation.
- richer question formats.
- analytics and engagement tracking.

## Implementation Status
- Complete: email-code registration, login, logout, authenticated identity, and initial platform-admin bootstrap.
- Complete: platform-admin promotion, user invitations, user removal safeguards, and a dedicated admin dashboard area.
- Complete: persistent teams, invite codes, optional approval, team-admin roles, membership approval/rejection/removal, and team selection.
- Complete: team-scoped master cycles, trivia access, answers, trophies, leaderboard, history, and basic engagement analytics.
- Complete: manual multiple-choice trivia creation plus one-question AI challenges with automatic publication, a configurable answer deadline, evaluation, and trophy awards.
- Complete: in-app notifications when team trivia is published.
- Deferred beyond the confirmed multiple-choice MVP: additional question formats and advanced analytics visualizations.
- External configuration required for production: SMTP credentials and a Groq API key. Local development uses console email; AI generation requires a configured key.
