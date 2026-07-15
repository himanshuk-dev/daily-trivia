import { Box, Button, Card, CardContent, Grid, Paper, Radio, RadioGroup, Stack, Typography } from '@mui/material'

const fallbackChoices = ['Option A', 'Option B', 'Option C', 'Option D']

export function LiveTrivia({ session, questions, choices, setChoices, canManage, onSubmit, onPublish, onEvaluate }) {
  return (
    <Grid item xs={12}>
      <Card sx={{ borderRadius: 4 }}><CardContent>
        <Typography variant="h6" gutterBottom>Live trivia session</Typography>
        {!session ? <Typography color="text.secondary">Load a trivia session to preview and answer it.</Typography> : (
          <Stack spacing={3}>
            <Box>
              <Typography variant="h5" fontWeight={800}>{session.title}</Typography>
              <Typography color="text.secondary">Topic: {session.topic}</Typography>
              {session.status === 'live' && session.close_at ? <Typography color="warning.dark" fontWeight={800}>Answers close {new Date(session.close_at).toLocaleString()}</Typography> : null}
            </Box>
            {questions.map((question, index) => (
              <Paper key={question.id} variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
                <Typography fontWeight={700} gutterBottom>Q{index + 1}. {question.prompt}</Typography>
                <RadioGroup value={choices[question.id] ?? question.choices?.[0] ?? 'Option A'} onChange={(event) => setChoices((current) => ({ ...current, [question.id]: event.target.value }))}>
                  {(question.choices?.length ? question.choices : fallbackChoices).map((choice) => (
                    <Box key={choice} sx={{ display: 'flex', alignItems: 'center' }}><Radio value={choice} /><Typography>{choice}</Typography></Box>
                  ))}
                </RadioGroup>
              </Paper>
            ))}
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <Button variant="contained" onClick={onSubmit} disabled={session.status !== 'live'}>Submit answer</Button>
              {canManage && session.status === 'draft' ? <Button variant="outlined" onClick={onPublish}>Publish session</Button> : null}
              {canManage && session.status === 'live' ? <Button variant="outlined" onClick={onEvaluate}>Close and evaluate</Button> : null}
            </Stack>
          </Stack>
        )}
      </CardContent></Card>
    </Grid>
  )
}
