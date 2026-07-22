import { Backdrop, Box, Button, Card, CardContent, CircularProgress, Divider, Grid, List, ListItem, ListItemText, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material'
import { formatDate } from '../utils/dates'

const suggestedTopics = [
  'Arts and Literature', 'Canadian History', 'Current Events', 'Food and Cuisine',
  'Geography', 'Health and Wellness', 'Movies and Television', 'Music',
  'Nature and Wildlife', 'Science', 'Space', 'Sports', 'Technology', 'World History',
]

export function TriviaBuilder({ builder, cycles, setBuilder, onLoadDraft, onAddQuestion, onSave, onGenerate, isGenerating }) {
  if (!cycles.length) return null
  const selectedCycle = cycles.find((cycle) => String(cycle.id) === String(builder.cycleId))
  const today = formatDate(new Date())
  const scheduledTopic = selectedCycle?.daily_topics?.find((item) => item.date === today)?.topic
  const selectedCycleDrafts = selectedCycle?.trivia_sessions?.filter((session) => session.status === 'draft') ?? []
  return (
    <Grid item xs={12}>
      <Card sx={{ borderRadius: 4 }}><CardContent>
        <Typography variant="h6" gutterBottom>Daily AI trivia</Typography>
        <Typography color="text.secondary">Select the cycle for your topic, then let AI create and publish one question for the configured answer window.</Typography>
        <Stack spacing={2}>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <TextField select fullWidth label="Master cycle" value={builder.cycleId} onChange={(event) => setBuilder((current) => ({ ...current, cycleId: event.target.value, sessionId: '', aiTopic: '', questions: [] }))}>
                {cycles.map((cycle) => <MenuItem key={cycle.id} value={String(cycle.id)}>{cycle.topic} · {cycle.master_name}</MenuItem>)}
              </TextField>
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                select
                fullWidth
                label="Draft selection"
                value={builder.sessionId}
                onChange={(event) => onLoadDraft(event.target.value)}
                SelectProps={{
                  displayEmpty: true,
                  renderValue: (value) => selectedCycleDrafts.find((session) => String(session.id) === String(value))?.title ?? 'New draft',
                }}
              >
                <MenuItem value="">New draft</MenuItem>
                {selectedCycleDrafts.map((session) => (
                  <MenuItem key={session.id} value={String(session.id)}>{session.title}</MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} md={4}><TextField fullWidth label="Trivia title" value={builder.title} onChange={(event) => setBuilder((current) => ({ ...current, title: event.target.value }))} /></Grid>
          </Grid>
          {selectedCycle ? (
            <TextField select fullWidth label="Today’s trivia topic" value={builder.aiTopic} onChange={(event) => setBuilder((current) => ({ ...current, aiTopic: event.target.value }))}>
              {scheduledTopic ? <MenuItem value={scheduledTopic}>{scheduledTopic} · Previously scheduled</MenuItem> : null}
              {suggestedTopics.filter((topic) => topic !== scheduledTopic).map((topic) => <MenuItem key={topic} value={topic}>{topic}</MenuItem>)}
            </TextField>
          ) : null}
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
            <Button variant="contained" color="warning" onClick={onGenerate} disabled={!builder.cycleId || !builder.aiTopic || Boolean(builder.sessionId) || isGenerating}>
              {isGenerating ? 'Generating trivia…' : 'Generate & publish AI question'}
            </Button>
          </Stack>
        </Stack>
        <Backdrop open={isGenerating} sx={{ color: 'white', zIndex: (theme) => theme.zIndex.modal + 1 }}>
          <Paper sx={{ p: 4, borderRadius: 4, textAlign: 'center', maxWidth: 420 }}>
            <CircularProgress color="secondary" size={56} />
            <Box sx={{ mt: 2 }}>
              <Typography variant="h6" fontWeight={800}>Creating today’s trivia…</Typography>
              <Typography color="text.secondary">AI is preparing and publishing one question. This may take a few moments.</Typography>
            </Box>
          </Paper>
        </Backdrop>
      </CardContent></Card>
    </Grid>
  )
}
