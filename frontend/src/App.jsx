import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  AppBar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  CssBaseline,
  Divider,
  Grid,
  List,
  ListItem,
  ListItemText,
  Paper,
  Radio,
  RadioGroup,
  Stack,
  TextField,
  Toolbar,
  Typography,
} from '@mui/material'
import EmojiEventsIcon from '@mui/icons-material/EmojiEvents'
import { api } from './api'

const sampleChoices = ['Option A', 'Option B', 'Option C', 'Option D']

export default function App() {
  const [username, setUsername] = useState('')
  const [createdUser, setCreatedUser] = useState(null)
  const [leaderboard, setLeaderboard] = useState([])
  const [cycles, setCycles] = useState([])
  const [activeSession, setActiveSession] = useState(null)
  const [selectedChoices, setSelectedChoices] = useState({})
  const [message, setMessage] = useState('')

  useEffect(() => {
    api.getLeaderboard().then(setLeaderboard).catch(() => setLeaderboard([]))
    api.getMasterCycles().then(setCycles).catch(() => setCycles([]))
  }, [])

  const activeQuestions = useMemo(() => activeSession?.questions ?? [], [activeSession])

  const handleCreateUser = async () => {
    const user = await api.createUser(username)
    setCreatedUser(user)
    setMessage(`Created user ${user.username}`)
    setUsername('')
  }

  const handleLoadFirstSession = async () => {
    const firstSessionId = cycles[0]?.trivia_sessions?.[0]?.id
    if (!firstSessionId) {
      setMessage('No trivia session available yet.')
      return
    }

    const session = await api.getTriviaSession(firstSessionId)
    setActiveSession(session)
    setMessage(`Loaded trivia session: ${session.title}`)
  }

  const handleSubmitAnswer = async () => {
    if (!createdUser || !activeSession) {
      setMessage('Create a user and load a session first.')
      return
    }

    await Promise.all(
      activeQuestions.map((question) =>
        api.submitAnswer(activeSession.id, {
          user: createdUser.id,
          trivia_question: question.id,
          selected_choice: selectedChoices[question.id] ?? question.choices?.[0] ?? 'Option A',
        }),
      ),
    )
    setMessage('Answers submitted.')
  }

  return (
    <>
      <CssBaseline />
      <AppBar position="static" color="transparent" elevation={0}>
        <Toolbar sx={{ justifyContent: 'space-between' }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <EmojiEventsIcon color="warning" />
            <Typography variant="h6" fontWeight={800}>
              Daily Trivia
            </Typography>
          </Stack>
          <Chip label="React + Material UI" color="primary" variant="outlined" />
        </Toolbar>
      </AppBar>

      <Box sx={{ py: 4, minHeight: '100vh', background: 'linear-gradient(180deg, #0f172a 0%, #111827 35%, #f3f4f6 35%, #f3f4f6 100%)' }}>
        <Container maxWidth="lg">
          <Box sx={{ color: 'white', mb: 4 }}>
            <Typography variant="overline" letterSpacing={4}>
              Biweekly trivia battles
            </Typography>
            <Typography variant="h2" fontWeight={900} sx={{ maxWidth: 760 }}>
              AI-generated trivia, master-approved publishing, and trophies for every correct user.
            </Typography>
          </Box>

          {message ? <Alert severity="info" sx={{ mb: 3 }}>{message}</Alert> : null}

          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Card sx={{ borderRadius: 4 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Create username
                  </Typography>
                  <Stack spacing={2}>
                    <TextField
                      label="Username"
                      value={username}
                      onChange={(event) => setUsername(event.target.value)}
                      fullWidth
                    />
                    <Button variant="contained" onClick={handleCreateUser} disabled={!username.trim()}>
                      Create user
                    </Button>
                    {createdUser ? (
                      <Chip label={`Active user: ${createdUser.username}`} color="success" />
                    ) : null}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={4}>
              <Card sx={{ borderRadius: 4, height: '100%' }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Current cycles
                  </Typography>
                  <List dense disablePadding>
                    {cycles.length === 0 ? (
                      <ListItem disableGutters>
                        <ListItemText primary="No cycles yet" secondary="Create one from the backend admin flow." />
                      </ListItem>
                    ) : (
                      cycles.map((cycle) => (
                        <Box key={cycle.id} sx={{ mb: 2 }}>
                          <Typography fontWeight={700}>{cycle.topic}</Typography>
                          <Typography variant="body2" color="text.secondary">
                            Master: {cycle.master_name} | Status: {cycle.status}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {cycle.start_date} to {cycle.end_date}
                          </Typography>
                          <Divider sx={{ my: 1 }} />
                        </Box>
                      ))
                    )}
                  </List>
                  <Button sx={{ mt: 1 }} variant="outlined" onClick={handleLoadFirstSession}>
                    Load first trivia session
                  </Button>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={4}>
              <Card sx={{ borderRadius: 4, height: '100%' }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Public leaderboard
                  </Typography>
                  <Stack spacing={1}>
                    {leaderboard.length === 0 ? (
                      <Typography variant="body2" color="text.secondary">
                        Leaderboard appears after correct answers are evaluated.
                      </Typography>
                    ) : (
                      leaderboard.map((entry, index) => (
                        <Paper key={entry.user_id} variant="outlined" sx={{ p: 1.5, borderRadius: 3 }}>
                          <Stack direction="row" justifyContent="space-between" alignItems="center">
                            <Typography fontWeight={700}>
                              #{index + 1} {entry.username}
                            </Typography>
                            <Chip label={`${entry.trophy_count} trophies`} color="warning" />
                          </Stack>
                        </Paper>
                      ))
                    )}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12}>
              <Card sx={{ borderRadius: 4 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Live trivia session
                  </Typography>
                  {!activeSession ? (
                    <Typography color="text.secondary">
                      Load a trivia session to preview and answer it.
                    </Typography>
                  ) : (
                    <Stack spacing={3}>
                      <Box>
                        <Typography variant="h5" fontWeight={800}>
                          {activeSession.title}
                        </Typography>
                        <Typography color="text.secondary">Topic: {activeSession.topic}</Typography>
                      </Box>

                      {activeQuestions.map((question, index) => (
                        <Paper key={question.id} variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
                          <Typography fontWeight={700} gutterBottom>
                            Q{index + 1}. {question.prompt}
                          </Typography>
                          <RadioGroup
                            value={selectedChoices[question.id] ?? question.choices?.[0] ?? 'Option A'}
                            onChange={(event) =>
                              setSelectedChoices((current) => ({
                                ...current,
                                [question.id]: event.target.value,
                              }))
                            }
                          >
                            {(question.choices?.length ? question.choices : sampleChoices).map((choice) => (
                              <Box key={choice} sx={{ display: 'flex', alignItems: 'center' }}>
                                <Radio value={choice} />
                                <Typography>{choice}</Typography>
                              </Box>
                            ))}
                          </RadioGroup>
                        </Paper>
                      ))}

                      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                        <Button variant="contained" onClick={handleSubmitAnswer} disabled={!createdUser}>
                          Submit answer
                        </Button>
                        <Button variant="outlined" onClick={() => api.evaluateTriviaSession(activeSession.id)}>
                          Evaluate session
                        </Button>
                      </Stack>
                    </Stack>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Container>
      </Box>
    </>
  )
}
