import { Button, Card, CardContent, Divider, Grid, List, ListItem, ListItemText, MenuItem, Stack, TextField, Typography } from '@mui/material'

export function TriviaBuilder({ builder, cycles, setBuilder, onLoadDraft, onAddQuestion, onSave, onGenerate }) {
  if (!cycles.length) return null
  return (
    <Grid item xs={12}>
      <Card sx={{ borderRadius: 4 }}><CardContent>
        <Typography variant="h6" gutterBottom>Master trivia builder</Typography>
        <Stack spacing={2}>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <TextField select fullWidth label="Master cycle" value={builder.cycleId} onChange={(event) => setBuilder((current) => ({ ...current, cycleId: event.target.value, sessionId: '', questions: [] }))}>
                {cycles.map((cycle) => <MenuItem key={cycle.id} value={String(cycle.id)}>{cycle.topic} · {cycle.master_name}</MenuItem>)}
              </TextField>
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField select fullWidth label="Edit existing draft" value={builder.sessionId} onChange={(event) => onLoadDraft(event.target.value)}>
                <MenuItem value="">New draft</MenuItem>
                {cycles.flatMap((cycle) => cycle.trivia_sessions).filter((session) => session.status === 'draft').map((session) => (
                  <MenuItem key={session.id} value={String(session.id)}>{session.title}</MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} md={4}><TextField fullWidth label="Trivia title" value={builder.title} onChange={(event) => setBuilder((current) => ({ ...current, title: event.target.value }))} /></Grid>
          </Grid>
          <Divider />
          <TextField fullWidth label="Question" value={builder.prompt} onChange={(event) => setBuilder((current) => ({ ...current, prompt: event.target.value }))} />
          <Grid container spacing={2}>
            {builder.choices.map((choice, index) => (
              <Grid item xs={12} sm={6} key={index}>
                <TextField fullWidth label={`Choice ${index + 1}`} value={choice} onChange={(event) => setBuilder((current) => ({
                  ...current,
                  choices: current.choices.map((item, itemIndex) => itemIndex === index ? event.target.value : item),
                }))} />
              </Grid>
            ))}
          </Grid>
          <TextField select fullWidth label="Correct choice" value={builder.correct_choice} onChange={(event) => setBuilder((current) => ({ ...current, correct_choice: event.target.value }))}>
            {builder.choices.filter(Boolean).map((choice) => <MenuItem key={choice} value={choice}>{choice}</MenuItem>)}
          </TextField>
          <TextField fullWidth label="Explanation" value={builder.explanation} onChange={(event) => setBuilder((current) => ({ ...current, explanation: event.target.value }))} />
          <Button variant="outlined" onClick={onAddQuestion}>Add question to draft</Button>
          <List dense>{builder.questions.map((question, index) => (
            <ListItem key={`${question.prompt}-${index}`} secondaryAction={<Button color="error" onClick={() => setBuilder((current) => ({ ...current, questions: current.questions.filter((_, itemIndex) => itemIndex !== index) }))}>Remove</Button>}>
              <ListItemText primary={`${index + 1}. ${question.prompt}`} secondary={`Correct: ${question.correct_choice}`} />
            </ListItem>
          ))}</List>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <Button variant="contained" onClick={onSave} disabled={!builder.cycleId || builder.questions.length === 0}>{builder.sessionId ? 'Save draft changes' : 'Create manual draft'}</Button>
            <Button variant="outlined" onClick={onGenerate} disabled={!builder.cycleId || Boolean(builder.sessionId)}>Generate AI draft</Button>
          </Stack>
        </Stack>
      </CardContent></Card>
    </Grid>
  )
}
