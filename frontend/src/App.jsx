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

export default function App() {
  const today = useMemo(() => formatDate(new Date()), [])
  const [authMode, setAuthMode] = useState('login')
  const [authStep, setAuthStep] = useState('request')
  const [authEmail, setAuthEmail] = useState('')
  const [authUsername, setAuthUsername] = useState('')
  const [authCode, setAuthCode] = useState('')
  const [managedUsername, setManagedUsername] = useState('')
  const [managedEmail, setManagedEmail] = useState('')
  const [createdUser, setCreatedUser] = useState(null)
  const [authLoading, setAuthLoading] = useState(true)
  const [dashboardView, setDashboardView] = useState('user')
  const [users, setUsers] = useState([])
  const [teams, setTeams] = useState([])
  const [selectedTeamId, setSelectedTeamId] = useState('')
  const [inviteCode, setInviteCode] = useState('')
  const [teamMembers, setTeamMembers] = useState([])
  const [teamAnalytics, setTeamAnalytics] = useState(null)
  const [notifications, setNotifications] = useState([])
  const [newTeam, setNewTeam] = useState({ name: '', approval_required: true })
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
  const [builder, setBuilder] = useState({
    cycleId: '',
    sessionId: '',
    title: '',
    prompt: '',
    choices: ['', '', '', ''],
    correct_choice: '',
    explanation: '',
    questions: [],
  })

  useEffect(() => {
    if (!api.hasToken()) {
      setAuthLoading(false)
      return
    }

    api.getMe()
      .then(setCreatedUser)
      .catch(() => api.clearToken())
      .finally(() => setAuthLoading(false))
  }, [])

  useEffect(() => {
    if (!createdUser) return
    api.getUsers().then(setUsers).catch(() => setUsers([]))
    api.getTeams().then((data) => {
      setTeams(data)
      const approvedTeam = data.find((team) => team.membership_status === 'approved')
      if (approvedTeam) setSelectedTeamId(String(approvedTeam.id))
    }).catch(() => setTeams([]))
    api.getMasterCycles().then(setCycles).catch(() => setCycles([]))
    api.getNotifications().then(setNotifications).catch(() => setNotifications([]))
  }, [createdUser])

  useEffect(() => {
    if (!selectedTeamId) {
      setLeaderboard([])
      setTeamMembers([])
      return
    }
    api.getTeamLeaderboard(selectedTeamId).then(setLeaderboard).catch(() => setLeaderboard([]))
    const team = teams.find((candidate) => String(candidate.id) === String(selectedTeamId))
    if (createdUser?.is_staff || team?.membership_role === 'team_admin') {
      api.getTeamMembers(selectedTeamId).then(setTeamMembers).catch(() => setTeamMembers([]))
      api.getTeamAnalytics(selectedTeamId).then(setTeamAnalytics).catch(() => setTeamAnalytics(null))
    } else {
      setTeamMembers([])
      setTeamAnalytics(null)
    }
  }, [createdUser, selectedTeamId, teams])

  useEffect(() => {
    if (createdUser && !masterCycle.master_username) {
      setMasterCycle((current) => ({ ...current, master_username: createdUser.username }))
    }
  }, [createdUser, masterCycle.master_username])

  const activeQuestions = useMemo(() => activeSession?.questions ?? [], [activeSession])
  const selectedTeam = useMemo(
    () => teams.find((team) => String(team.id) === String(selectedTeamId)),
    [selectedTeamId, teams],
  )
  const canManageSelectedTeam = createdUser?.is_staff || selectedTeam?.membership_role === 'team_admin'
  const manageableCycles = useMemo(
    () => cycles.filter((cycle) => createdUser?.is_staff || cycle.master_name === createdUser?.username),
    [createdUser, cycles],
  )
  const canManageActiveSession = useMemo(() => {
    const cycle = cycles.find((item) => item.id === activeSession?.master_cycle)
    return Boolean(cycle && (createdUser?.is_staff || cycle.master_name === createdUser?.username))
  }, [activeSession, createdUser, cycles])

  const handleRequestCode = async () => {
    try {
      await api.requestCode({
        email: authEmail.trim(),
        ...(authMode === 'register' ? { username: authUsername.trim() } : {}),
      })
      setAuthStep('verify')
      setMessage(`A login code was sent to ${authEmail.trim()}.`)
    } catch (error) {
      setMessage(error.message)
    }
  }

  const handleVerifyCode = async () => {
    try {
      const result = await api.verifyCode({ email: authEmail.trim(), code: authCode.trim() })
      api.setToken(result.token)
      setCreatedUser(result.user)
      setAuthCode('')
      setMessage(`Welcome, ${result.user.username}.`)
    } catch (error) {
      setMessage(error.message)
    }
  }

  const handleLogout = async () => {
    try {
      await api.logout()
    } finally {
      api.clearToken()
      setCreatedUser(null)
      setUsers([])
      setTeams([])
      setSelectedTeamId('')
      setCycles([])
      setLeaderboard([])
      setAuthStep('request')
      setMessage('You have been logged out.')
    }
  }

  const handleCreateMasterCycle = async () => {
    try {
      const cycle = await api.createMasterCycle({ ...masterCycle, team: selectedTeamId, status: 'active' })
      setCycles((current) => [cycle, ...current])
      setMasterCycle((current) => ({ ...current, topic: '' }))
      setMessage(`${cycle.master_name} is now the master for ${cycle.topic}.`)
    } catch (error) {
      setMessage(error.message)
    }
  }

  const handleJoinTeam = async () => {
    try {
      const membership = await api.joinTeam(inviteCode.trim())
      const refreshedTeams = await api.getTeams()
      setTeams(refreshedTeams)
      setInviteCode('')
      setSelectedTeamId(String(membership.team))
      setMessage(membership.status === 'approved' ? 'You joined the team.' : 'Your membership is awaiting approval.')
    } catch (error) {
      setMessage(error.message)
    }
  }

  const handleCreateTeam = async () => {
    try {
      const team = await api.createTeam(newTeam)
      setTeams((current) => [...current, team].sort((a, b) => a.name.localeCompare(b.name)))
      setSelectedTeamId(String(team.id))
      setNewTeam({ name: '', approval_required: true })
      setMessage(`Created team ${team.name}. Invite code: ${team.invite_code}`)
    } catch (error) {
      setMessage(error.message)
    }
  }

  const handleMembershipUpdate = async (membership, payload) => {
    try {
      const updated = await api.updateTeamMember(selectedTeamId, membership.id, payload)
      setTeamMembers((current) => current.map((item) => (item.id === updated.id ? updated : item)))
      setMessage(`Updated ${updated.username}.`)
    } catch (error) {
      setMessage(error.message)
    }
  }

  const handleRemoveMembership = async (membership) => {
    try {
      await api.removeTeamMember(selectedTeamId, membership.id)
      setTeamMembers((current) => current.filter((item) => item.id !== membership.id))
      setMessage(`Removed ${membership.username} from ${selectedTeam.name}.`)
    } catch (error) {
      setMessage(error.message)
    }
  }

  const handleAdminToggle = async (user) => {
    try {
      const updated = await api.setPlatformAdmin(user.id, !user.is_staff)
      setUsers((current) => current.map((item) => (item.id === updated.id ? updated : item)))
      setMessage(`${updated.username} ${updated.is_staff ? 'is now' : 'is no longer'} a platform admin.`)
    } catch (error) {
      setMessage(error.message)
    }
  }

  const handleAddQuestion = () => {
    const choices = builder.choices.map((choice) => choice.trim()).filter(Boolean)
    if (!builder.prompt.trim() || choices.length < 2 || !choices.includes(builder.correct_choice)) {
      setMessage('Add a prompt, at least two choices, and select the correct choice.')
      return
    }
    setBuilder((current) => ({
      ...current,
      questions: [...current.questions, {
        prompt: current.prompt.trim(),
        choices,
        correct_choice: current.correct_choice,
        explanation: current.explanation.trim(),
      }],
      prompt: '',
      choices: ['', '', '', ''],
      correct_choice: '',
      explanation: '',
    }))
  }

  const handleCreateTrivia = async () => {
    try {
      const payload = { title: builder.title, questions: builder.questions }
      const session = builder.sessionId
        ? await api.updateTrivia(builder.sessionId, payload)
        : await api.createTrivia(builder.cycleId, payload)
      const refreshedCycles = await api.getMasterCycles()
      setCycles(refreshedCycles)
      setBuilder((current) => ({ ...current, sessionId: String(session.id), title: session.title, questions: session.questions }))
      setMessage(`Saved draft trivia: ${session.title}.`)
    } catch (error) {
      setMessage(error.message)
    }
  }

  const handleGenerateTrivia = async () => {
    try {
      const session = await api.generateTrivia(builder.cycleId, { title: builder.title, question_count: 5 })
      setCycles(await api.getMasterCycles())
      setBuilder((current) => ({
        ...current,
        sessionId: String(session.id),
        title: session.title,
        questions: session.questions,
      }))
      setMessage(`Generated AI draft: ${session.title}.`)
    } catch (error) {
      setMessage(error.message)
    }
  }

  const handleLoadDraft = async (sessionId) => {
    if (!sessionId) {
      setBuilder((current) => ({ ...current, sessionId: '', title: '', questions: [] }))
      return
    }
    try {
      const session = await api.getTriviaSession(sessionId)
      setBuilder((current) => ({
        ...current,
        cycleId: String(session.master_cycle),
        sessionId: String(session.id),
        title: session.title,
        questions: session.questions,
      }))
    } catch (error) {
      setMessage(error.message)
    }
  }

  const handleMasterAddUser = async () => {
    try {
      await api.requestCode({ username: managedUsername.trim(), email: managedEmail.trim() })
      setManagedUsername('')
      setManagedEmail('')
      setMessage(`Sent an account verification code to ${managedEmail.trim()}.`)
    } catch (error) {
      setMessage(error.message)
    }
  }

  const handleRemoveUser = async (user) => {
    try {
      await api.deleteUser(user.id)
      setUsers((current) => current.filter((candidate) => candidate.id !== user.id))
      setLeaderboard((current) => current.filter((entry) => entry.user_id !== user.id))
      setMessage(`Removed user ${user.username}.`)
    } catch (error) {
      setMessage(error.message)
    }
  }

  if (authLoading) {
    return <Box sx={{ p: 4 }}><Typography>Loading…</Typography></Box>
  }

  if (!createdUser) {
    return (
      <>
        <CssBaseline />
        <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', p: 2, background: '#0f172a' }}>
          <Card sx={{ width: '100%', maxWidth: 480, borderRadius: 4 }}>
            <CardContent sx={{ p: 4 }}>
              <Stack spacing={3}>
                <Box>
                  <Typography variant="h4" fontWeight={900}>Daily Trivia</Typography>
                  <Typography color="text.secondary">Sign in securely with a one-time email code.</Typography>
                </Box>
                {message ? <Alert severity="info">{message}</Alert> : null}
                {authStep === 'request' ? (
                  <>
                    <Stack direction="row" spacing={1}>
                      <Button variant={authMode === 'login' ? 'contained' : 'outlined'} onClick={() => setAuthMode('login')}>Login</Button>
                      <Button variant={authMode === 'register' ? 'contained' : 'outlined'} onClick={() => setAuthMode('register')}>Register</Button>
                    </Stack>
                    {authMode === 'register' ? (
                      <TextField label="Username" value={authUsername} onChange={(event) => setAuthUsername(event.target.value)} />
                    ) : null}
                    <TextField label="Email" type="email" value={authEmail} onChange={(event) => setAuthEmail(event.target.value)} />
                    <Button
                      variant="contained"
                      onClick={handleRequestCode}
                      disabled={!authEmail.trim() || (authMode === 'register' && !authUsername.trim())}
                    >
                      Email me a code
                    </Button>
                  </>
                ) : (
                  <>
                    <TextField label="Six-digit code" value={authCode} onChange={(event) => setAuthCode(event.target.value)} inputProps={{ maxLength: 6 }} />
                    <Button variant="contained" onClick={handleVerifyCode} disabled={authCode.trim().length !== 6}>Verify and continue</Button>
                    <Button onClick={() => setAuthStep('request')}>Use a different email</Button>
                  </>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Box>
      </>
    )
  }

  const handleLoadFirstSession = async () => {
    const teamCycle = cycles.find((cycle) => String(cycle.team) === String(selectedTeamId) && cycle.trivia_sessions?.length)
    const preferredSession = teamCycle?.trivia_sessions?.find((session) => session.status === 'live')
      ?? (createdUser?.is_staff || teamCycle?.master_name === createdUser?.username ? teamCycle?.trivia_sessions?.[0] : null)
    const firstSessionId = preferredSession?.id
    if (!firstSessionId) {
      setMessage('No trivia session available yet.')
      return
    }

    const session = await api.getTriviaSession(firstSessionId)
    setActiveSession(session)
    setMessage(`Loaded trivia session: ${session.title}`)
  }

  const handlePublishSession = async () => {
    try {
      const session = await api.publishTriviaSession(activeSession.id)
      setActiveSession(session)
      setCycles(await api.getMasterCycles())
      setMessage(`${session.title} is now live.`)
    } catch (error) {
      setMessage(error.message)
    }
  }

  const handleEvaluateSession = async () => {
    try {
      const result = await api.evaluateTriviaSession(activeSession.id)
      setCycles(await api.getMasterCycles())
      setLeaderboard(selectedTeamId ? await api.getTeamLeaderboard(selectedTeamId) : [])
      setMessage(`Evaluation complete. Awarded ${result.trophies_awarded} trophies.`)
    } catch (error) {
      setMessage(error.message)
    }
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
          <Stack direction="row" spacing={1}>
            <Button variant={dashboardView === 'user' ? 'contained' : 'text'} onClick={() => setDashboardView('user')}>User dashboard</Button>
            {createdUser.is_staff ? (
              <Button variant={dashboardView === 'admin' ? 'contained' : 'text'} onClick={() => setDashboardView('admin')}>Admin dashboard</Button>
            ) : null}
          </Stack>
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
                    Your account
                  </Typography>
                  <Stack spacing={2}>
                    <Chip label={`Signed in: ${createdUser.username}`} color="success" />
                    <Typography variant="body2" color="text.secondary">{createdUser.email}</Typography>
                    {createdUser.is_staff ? <Chip label="Platform admin" color="primary" /> : null}
                    <Typography variant="body2">{notifications.filter((item) => !item.read_at).length} unread notifications</Typography>
                    {notifications.filter((item) => !item.read_at).slice(0, 2).map((notification) => (
                      <Alert key={notification.id} severity="info">{notification.message}</Alert>
                    ))}
                    {notifications.some((item) => !item.read_at) ? (
                      <Button size="small" onClick={async () => { await api.markNotificationsRead(); setNotifications((current) => current.map((item) => ({ ...item, read_at: new Date().toISOString() }))) }}>Mark read</Button>
                    ) : null}
                    <Button variant="outlined" onClick={handleLogout}>Logout</Button>
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
                  <Typography variant="h6" gutterBottom>Teams</Typography>
                  <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mb: 2 }}>
                    <TextField
                      select
                      fullWidth
                      label="Current team"
                      value={selectedTeamId}
                      onChange={(event) => setSelectedTeamId(event.target.value)}
                    >
                      {teams.map((team) => (
                        <MenuItem key={team.id} value={String(team.id)}>
                          {team.name} ({team.membership_status})
                        </MenuItem>
                      ))}
                    </TextField>
                    <TextField label="Invite code" value={inviteCode} onChange={(event) => setInviteCode(event.target.value)} fullWidth />
                    <Button variant="outlined" onClick={handleJoinTeam} disabled={!inviteCode.trim()} sx={{ minWidth: 120 }}>Join team</Button>
                  </Stack>
                  {selectedTeam ? (
                    <Alert severity={selectedTeam.membership_status === 'approved' ? 'success' : 'warning'}>
                      {selectedTeam.name} · {selectedTeam.member_count} members
                      {canManageSelectedTeam ? ` · Invite code: ${selectedTeam.invite_code}` : ''}
                    </Alert>
                  ) : <Typography color="text.secondary">Join a team to access its trivia.</Typography>}
                </CardContent>
              </Card>
            </Grid>

            {createdUser.is_staff && dashboardView === 'admin' ? (
              <Grid item xs={12}>
                <Card sx={{ borderRadius: 4 }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>Platform admin dashboard</Typography>
                    <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mb: 2 }}>
                      <TextField label="New team name" value={newTeam.name} onChange={(event) => setNewTeam((current) => ({ ...current, name: event.target.value }))} fullWidth />
                      <TextField
                        select
                        label="Membership approval"
                        value={String(newTeam.approval_required)}
                        onChange={(event) => setNewTeam((current) => ({ ...current, approval_required: event.target.value === 'true' }))}
                        fullWidth
                      >
                        <MenuItem value="true">Admin approval required</MenuItem>
                        <MenuItem value="false">Join immediately</MenuItem>
                      </TextField>
                      <Button variant="contained" onClick={handleCreateTeam} disabled={!newTeam.name.trim()} sx={{ minWidth: 140 }}>Create team</Button>
                    </Stack>
                    <Typography variant="subtitle2">Platform administrators</Typography>
                    <List dense>
                      {users.map((user) => (
                        <ListItem key={user.id} disableGutters secondaryAction={(
                          <Button onClick={() => handleAdminToggle(user)} disabled={user.id === createdUser.id}>
                            {user.is_staff ? 'Remove admin' : 'Make admin'}
                          </Button>
                        )}>
                          <ListItemText primary={user.username} secondary={`${user.email}${user.is_staff ? ' · Admin' : ''}`} />
                        </ListItem>
                      ))}
                    </List>
                  </CardContent>
                </Card>
              </Grid>
            ) : null}

            {canManageSelectedTeam ? (
              <Grid item xs={12}>
                <Card sx={{ borderRadius: 4 }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>Team administration</Typography>
                    {teamAnalytics ? (
                      <Alert severity="info" sx={{ mb: 2 }}>
                        {teamAnalytics.approved_members} members · {teamAnalytics.pending_members} pending · {teamAnalytics.trivia_sessions} sessions · {teamAnalytics.answers} answers · {teamAnalytics.trophies} trophies
                      </Alert>
                    ) : null}
                    <List dense>
                      {teamMembers.map((membership) => (
                        <ListItem key={membership.id} disableGutters>
                          <ListItemText primary={membership.username} secondary={`${membership.email} · ${membership.role} · ${membership.status}`} />
                          <Stack direction="row" spacing={1}>
                            {membership.status === 'pending' ? (
                              <>
                                <Button onClick={() => handleMembershipUpdate(membership, { status: 'approved' })}>Approve</Button>
                                <Button color="error" onClick={() => handleMembershipUpdate(membership, { status: 'rejected' })}>Reject</Button>
                              </>
                            ) : null}
                            {membership.status === 'approved' && membership.user !== createdUser.id ? (
                              <Button onClick={() => handleMembershipUpdate(membership, { role: membership.role === 'team_admin' ? 'member' : 'team_admin' })}>
                                {membership.role === 'team_admin' ? 'Make member' : 'Make team admin'}
                              </Button>
                            ) : null}
                            {membership.user !== createdUser.id ? <Button color="error" onClick={() => handleRemoveMembership(membership)}>Remove</Button> : null}
                          </Stack>
                        </ListItem>
                      ))}
                    </List>
                  </CardContent>
                </Card>
              </Grid>
            ) : null}

            {canManageSelectedTeam ? <Grid item xs={12}>
              <Card sx={{ borderRadius: 4 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Add master
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Select an approved {selectedTeam?.name} member to lead the next two-week trivia cycle.
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
                        {teamMembers.filter((membership) => membership.status === 'approved').map((membership) => (
                          <MenuItem key={membership.user} value={membership.username}>{membership.username}</MenuItem>
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
            </Grid> : null}

            {createdUser.is_staff && dashboardView === 'admin' ? (
              <Grid item xs={12}>
                <Card sx={{ borderRadius: 4 }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Platform user management
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      Invite new accounts by email or remove accounts that have no protected master-cycle history.
                    </Typography>
                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
                      <TextField
                        label="New username"
                        value={managedUsername}
                        onChange={(event) => setManagedUsername(event.target.value)}
                        fullWidth
                      />
                      <TextField
                        label="Email"
                        type="email"
                        value={managedEmail}
                        onChange={(event) => setManagedEmail(event.target.value)}
                        fullWidth
                      />
                      <Button
                        variant="contained"
                        onClick={handleMasterAddUser}
                        disabled={!managedUsername.trim() || !managedEmail.trim()}
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

            {manageableCycles.length > 0 ? (
              <Grid item xs={12}>
                <Card sx={{ borderRadius: 4 }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>Master trivia builder</Typography>
                    <Stack spacing={2}>
                      <Grid container spacing={2}>
                        <Grid item xs={12} md={4}>
                          <TextField select fullWidth label="Master cycle" value={builder.cycleId} onChange={(event) => setBuilder((current) => ({ ...current, cycleId: event.target.value, sessionId: '', questions: [] }))}>
                            {manageableCycles.map((cycle) => <MenuItem key={cycle.id} value={String(cycle.id)}>{cycle.topic} · {cycle.master_name}</MenuItem>)}
                          </TextField>
                        </Grid>
                        <Grid item xs={12} md={4}>
                          <TextField select fullWidth label="Edit existing draft" value={builder.sessionId} onChange={(event) => handleLoadDraft(event.target.value)}>
                            <MenuItem value="">New draft</MenuItem>
                            {manageableCycles.flatMap((cycle) => cycle.trivia_sessions).filter((session) => session.status === 'draft').map((session) => (
                              <MenuItem key={session.id} value={String(session.id)}>{session.title}</MenuItem>
                            ))}
                          </TextField>
                        </Grid>
                        <Grid item xs={12} md={4}>
                          <TextField fullWidth label="Trivia title" value={builder.title} onChange={(event) => setBuilder((current) => ({ ...current, title: event.target.value }))} />
                        </Grid>
                      </Grid>
                      <Divider />
                      <TextField fullWidth label="Question" value={builder.prompt} onChange={(event) => setBuilder((current) => ({ ...current, prompt: event.target.value }))} />
                      <Grid container spacing={2}>
                        {builder.choices.map((choice, index) => (
                          <Grid item xs={12} sm={6} key={index}>
                            <TextField
                              fullWidth
                              label={`Choice ${index + 1}`}
                              value={choice}
                              onChange={(event) => setBuilder((current) => ({
                                ...current,
                                choices: current.choices.map((item, itemIndex) => itemIndex === index ? event.target.value : item),
                              }))}
                            />
                          </Grid>
                        ))}
                      </Grid>
                      <TextField select fullWidth label="Correct choice" value={builder.correct_choice} onChange={(event) => setBuilder((current) => ({ ...current, correct_choice: event.target.value }))}>
                        {builder.choices.filter(Boolean).map((choice) => <MenuItem key={choice} value={choice}>{choice}</MenuItem>)}
                      </TextField>
                      <TextField fullWidth label="Explanation" value={builder.explanation} onChange={(event) => setBuilder((current) => ({ ...current, explanation: event.target.value }))} />
                      <Button variant="outlined" onClick={handleAddQuestion}>Add question to draft</Button>
                      <List dense>
                        {builder.questions.map((question, index) => (
                          <ListItem key={`${question.prompt}-${index}`} secondaryAction={(
                            <Button color="error" onClick={() => setBuilder((current) => ({ ...current, questions: current.questions.filter((_, itemIndex) => itemIndex !== index) }))}>Remove</Button>
                          )}>
                            <ListItemText primary={`${index + 1}. ${question.prompt}`} secondary={`Correct: ${question.correct_choice}`} />
                          </ListItem>
                        ))}
                      </List>
                      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                        <Button variant="contained" onClick={handleCreateTrivia} disabled={!builder.cycleId || builder.questions.length === 0}>
                          {builder.sessionId ? 'Save draft changes' : 'Create manual draft'}
                        </Button>
                        <Button variant="outlined" onClick={handleGenerateTrivia} disabled={!builder.cycleId || Boolean(builder.sessionId)}>Generate AI draft</Button>
                      </Stack>
                    </Stack>
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
                        <Button variant="contained" onClick={handleSubmitAnswer} disabled={activeSession.status !== 'live'}>
                          Submit answer
                        </Button>
                        {canManageActiveSession && activeSession.status === 'draft' ? (
                          <Button variant="outlined" onClick={handlePublishSession}>Publish session</Button>
                        ) : null}
                        {canManageActiveSession && activeSession.status === 'live' ? (
                          <Button variant="outlined" onClick={handleEvaluateSession}>Close and evaluate</Button>
                        ) : null}
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
