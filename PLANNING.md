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

## Key Rules
- Usernames must be unique.
- Only the active master can create or publish trivia for the current cycle.
- AI-generated trivia should not go live without master approval.
- Trophy awards should be immutable once granted.
- Every award should be tied to a specific trivia session.

## Delivery Plan
### Phase 1
- User signup and identity.
- Master cycle setup.
- AI trivia generation.
- Publish and answer flow.
- Trophy awarding.

### Phase 2
- Leaderboards.
- Trivia history.
- Master review tools.
- Notifications for new live trivia.

### Phase 3
- Better AI validation.
- richer question formats.
- analytics and engagement tracking.

