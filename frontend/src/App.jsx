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
  MenuItem,
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
const ACTIVE_USER_KEY = 'daily-trivia-active-user'

function formatDate(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function addDays(dateString, days) {
  const date = new Date(`${dateString}T00:00:00`)
  date.setDate(date.getDate() + days)
  return formatDate(date)
}

function loadActiveUser() {
  try {
    return JSON.parse(localStorage.getItem(ACTIVE_USER_KEY))
  } catch {
    localStorage.removeItem(ACTIVE_USER_KEY)
    return null
  }
}

export default function App() {
  const today = useMemo(() => formatDate(new Date()), [])
  const [username, setUsername] = useState('')
  const [managedUsername, setManagedUsername] = useState('')
  const [createdUser, setCreatedUser] = useState(loadActiveUser)
  const [users, setUsers] = useState([])
  const [leaderboard, setLeaderboard] = useState([])
  const [cycles, setCycles] = useState([])
  const [masterCycle, setMasterCycle] = useState({
    master_username: '',
    topic: '',
    start_date: today,
    end_date: addDays(today, 13),
  })
  const [activeSession, setActiveSession] = useState(null)
  const [selectedChoices, setSelectedChoices] = useState({})
  const [message, setMessage] = useState('')

  useEffect(() => {
    api.getUsers().then(setUsers).catch(() => setUsers([]))
    api.getLeaderboard().then(setLeaderboard).catch(() => setLeaderboard([]))
    api.getMasterCycles().then(setCycles).catch(() => setCycles([]))
  }, [])

  useEffect(() => {
    if (createdUser && !masterCycle.master_username) {
      setMasterCycle((current) => ({ ...current, master_username: createdUser.username }))
    }
  }, [createdUser, masterCycle.master_username])

  const activeQuestions = useMemo(() => activeSession?.questions ?? [], [activeSession])
  const isActiveMaster = useMemo(
    () => cycles.some((cycle) => cycle.status === 'active' && cycle.master_name === createdUser?.username),
    [createdUser, cycles],
  )

  const handleCreateUser = async () => {
    try {
      const user = await api.createUser(username.trim())
      setCreatedUser(user)
      setUsers((current) => [...current, user].sort((a, b) => a.username.localeCompare(b.username)))
      localStorage.setItem(ACTIVE_USER_KEY, JSON.stringify(user))
      setMessage(`Created user ${user.username}`)
      setUsername('')
    } catch (error) {
      setMessage(error.message)
    }
  }

  const handleClearUser = () => {
    localStorage.removeItem(ACTIVE_USER_KEY)
    setCreatedUser(null)
    setMessage('Active user cleared from this browser.')
  }

  const handleSelectUser = (selectedUsername) => {
    const user = users.find((candidate) => candidate.username === selectedUsername)
    if (!user) return

    localStorage.setItem(ACTIVE_USER_KEY, JSON.stringify(user))
    setCreatedUser(user)
    setMessage(`Welcome back, ${user.username}.`)
  }

  const handleCreateMasterCycle = async () => {
    try {
      const cycle = await api.createMasterCycle({ ...masterCycle, status: 'active' })
      setCycles((current) => [cycle, ...current])
      setMasterCycle((current) => ({ ...current, topic: '' }))
      setMessage(`${cycle.master_name} is now the master for ${cycle.topic}.`)
    } catch (error) {
      setMessage(error.message)
    }
  }

  const handleMasterAddUser = async () => {
    try {
      const user = await api.createUser(managedUsername.trim())
      setUsers((current) => [...current, user].sort((a, b) => a.username.localeCompare(b.username)))
      setManagedUsername('')
      setMessage(`Added user ${user.username}.`)
    } catch (error) {
      setMessage(error.message)
    }
  }

  const handleRemoveUser = async (user) => {
    try {
      await api.deleteUser(user.id, createdUser.id)
      setUsers((current) => current.filter((candidate) => candidate.id !== user.id))
      setLeaderboard((current) => current.filter((entry) => entry.user_id !== user.id))
      setMessage(`Removed user ${user.username}.`)
    } catch (error) {
      setMessage(error.message)
    }
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
                    <Divider>or</Divider>
                    <TextField
                      select
                      label="Use existing user"
                      value={createdUser?.username ?? ''}
                      onChange={(event) => handleSelectUser(event.target.value)}
                      disabled={users.length === 0}
                      fullWidth
                    >
                      {users.map((user) => (
                        <MenuItem key={user.id} value={user.username}>{user.username}</MenuItem>
                      ))}
                    </TextField>
                    {createdUser ? (
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Chip label={`Active user: ${createdUser.username}`} color="success" />
                        <Button size="small" onClick={handleClearUser}>Forget</Button>
                      </Stack>
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
                        <ListItemText primary="No cycles yet" secondary="Use the Add master form below." />
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
                    Add master
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Select an existing user to lead the next two-week trivia cycle.
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={3}>
                      <TextField
                        select
                        fullWidth
                        label="Master"
                        value={masterCycle.master_username}
                        onChange={(event) => setMasterCycle((current) => ({ ...current, master_username: event.target.value }))}
                        disabled={users.length === 0}
                      >
                        {users.map((user) => (
                          <MenuItem key={user.id} value={user.username}>{user.username}</MenuItem>
                        ))}
                      </TextField>
                    </Grid>
                    <Grid item xs={12} md={3}>
                      <TextField
                        fullWidth
                        label="Trivia topic"
                        value={masterCycle.topic}
                        onChange={(event) => setMasterCycle((current) => ({ ...current, topic: event.target.value }))}
                      />
                    </Grid>
                    <Grid item xs={12} sm={6} md={2}>
                      <TextField
                        fullWidth
                        type="date"
                        label="Start date"
                        InputLabelProps={{ shrink: true }}
                        value={masterCycle.start_date}
                        onChange={(event) => setMasterCycle((current) => ({
                          ...current,
                          start_date: event.target.value,
                          end_date: addDays(event.target.value, 13),
                        }))}
                      />
                    </Grid>
                    <Grid item xs={12} sm={6} md={2}>
                      <TextField
                        fullWidth
                        type="date"
                        label="End date"
                        InputLabelProps={{ shrink: true }}
                        value={masterCycle.end_date}
                        onChange={(event) => setMasterCycle((current) => ({ ...current, end_date: event.target.value }))}
                      />
                    </Grid>
                    <Grid item xs={12} md={2}>
                      <Button
                        fullWidth
                        variant="contained"
                        sx={{ height: '100%' }}
                        onClick={handleCreateMasterCycle}
                        disabled={!masterCycle.master_username || !masterCycle.topic.trim()}
                      >
                        Add master
                      </Button>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>

            {isActiveMaster ? (
              <Grid item xs={12}>
                <Card sx={{ borderRadius: 4 }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Manage users
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      Active master tools for adding and removing trivia participants.
                    </Typography>
                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
                      <TextField
                        label="New username"
                        value={managedUsername}
                        onChange={(event) => setManagedUsername(event.target.value)}
                        fullWidth
                      />
                      <Button
                        variant="contained"
                        onClick={handleMasterAddUser}
                        disabled={!managedUsername.trim()}
                        sx={{ minWidth: 140 }}
                      >
                        Add user
                      </Button>
                    </Stack>
                    <List disablePadding>
                      {users.map((user) => (
                        <ListItem
                          key={user.id}
                          disableGutters
                          secondaryAction={(
                            <Button
                              color="error"
                              onClick={() => handleRemoveUser(user)}
                              disabled={user.id === createdUser.id}
                            >
                              Remove
                            </Button>
                          )}
                        >
                          <ListItemText
                            primary={user.username}
                            secondary={user.id === createdUser.id ? 'Current master' : null}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </CardContent>
                </Card>
              </Grid>
            ) : null}

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
