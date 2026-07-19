import { Alert, Box, Button, Card, CardContent, Grid, MenuItem, Paper, Radio, RadioGroup, Stack, TextField, Typography } from '@mui/material'

const fallbackChoices = ['Option A', 'Option B', 'Option C', 'Option D']

export function LiveTrivia({ session, sessions, questions, choices, setChoices, canManage, isSubmitting, onSubmit, onPublish, onEvaluate, onLoadSession }) {
  const answersClosed = Boolean(session && (
    session.status === 'closed' || (session.close_at && new Date(session.close_at) <= new Date())
  ))

  return (
    <Grid item xs={12}>
      <Card sx={{ borderRadius: 4 }}><CardContent>
        <Typography variant="h6" gutterBottom>Live trivia session</Typography>
        <TextField
          select
          fullWidth
          label="Current and previous trivia"
          value={session?.id ?? ''}
          onChange={(event) => onLoadSession(event.target.value)}
          sx={{ mb: 2 }}
        >
          {sessions.map((item) => (
            <MenuItem key={item.id} value={item.id}>
              {item.team_name ? `${item.team_name} · ` : ''}{item.title} · {item.status === 'closed' || (item.close_at && new Date(item.close_at) <= new Date()) ? 'answers available' : item.status}
            </MenuItem>
          ))}
        </TextField>
        {!session ? <Typography color="text.secondary">Load a trivia session to preview and answer it.</Typography> : (
          <Stack spacing={3}>
            <Box>
              <Typography variant="h5" fontWeight={800}>{session.title}</Typography>
              <Typography color="text.secondary">Topic: {session.topic}</Typography>
              {session.status === 'live' && session.close_at ? <Typography color="warning.dark" fontWeight={800}>Answers close {new Date(session.close_at).toLocaleString()}</Typography> : null}
            </Box>
            {canManage ? (
              <Paper variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2} sx={{ mb: 1 }}>
                  <Typography fontWeight={800}>Submissions ({session.submission_count ?? 0})</Typography>
                  <Button size="small" variant="text" onClick={() => onLoadSession(session.id)}>Refresh</Button>
                </Stack>
                {!session.submissions?.length ? (
                  <Typography color="text.secondary">No team members have submitted answers yet.</Typography>
                ) : (
                  <Stack spacing={1}>
                    {session.submissions.map((submission) => (
                      <Box key={submission.user_id} sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap' }}>
                        <Typography fontWeight={700}>{submission.username}</Typography>
                        <Typography color="text.secondary">
                          {submission.answers_submitted} {submission.answers_submitted === 1 ? 'answer' : 'answers'} · {new Date(submission.submitted_at).toLocaleString()}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                )}
              </Paper>
            ) : null}
            {answersClosed ? <Alert severity="success">This trivia has ended. Correct answers and your submitted answers are shown below.</Alert> : null}
            {session.has_submitted && !answersClosed ? (
              <Alert severity="success">
                Your answer is submitted. Results will be available after the Trivia Master closes and evaluates the trivia.
                {session.close_at ? ` This trivia closes ${new Date(session.close_at).toLocaleString()}.` : ''}
              </Alert>
            ) : null}
            {questions.map((question, index) => (
              <Paper key={question.id} variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
                <Typography fontWeight={700} gutterBottom>Q{index + 1}. {question.prompt}</Typography>
                <RadioGroup value={answersClosed || session.has_submitted ? (question.selected_choice ?? '') : (choices[question.id] ?? question.choices?.[0] ?? 'Option A')} onChange={(event) => setChoices((current) => ({ ...current, [question.id]: event.target.value }))}>
                  {(question.choices?.length ? question.choices : fallbackChoices).map((choice) => (
                    <Box key={choice} sx={{ display: 'flex', alignItems: 'center' }}><Radio value={choice} disabled={answersClosed || session.has_submitted} /><Typography fontWeight={answersClosed && choice === question.correct_choice ? 800 : 400} color={answersClosed && choice === question.correct_choice ? 'success.main' : 'text.primary'}>{choice}{answersClosed && choice === question.correct_choice ? ' — Correct answer' : ''}</Typography></Box>
                  ))}
                </RadioGroup>
                {answersClosed ? (
                  <Alert severity={question.is_correct ? 'success' : 'info'} sx={{ mt: 2 }}>
                    {question.selected_choice ? `Your answer: ${question.selected_choice}. ` : 'You did not submit an answer. '}
                    {question.explanation}
                  </Alert>
                ) : null}
              </Paper>
            ))}
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <Button variant="contained" onClick={onSubmit} disabled={session.status !== 'live' || answersClosed || session.has_submitted || isSubmitting}>
                {isSubmitting ? 'Submitting…' : session.has_submitted ? 'Answer submitted' : 'Submit answer'}
              </Button>
              {canManage && session.status === 'draft' ? <Button variant="outlined" onClick={onPublish}>Publish session</Button> : null}
              {canManage && session.status === 'live' ? <Button variant="outlined" onClick={onEvaluate}>Close and evaluate</Button> : null}
            </Stack>
          </Stack>
        )}
      </CardContent></Card>
    </Grid>
  )
}
