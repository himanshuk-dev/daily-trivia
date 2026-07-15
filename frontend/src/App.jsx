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
import { api } from './api'
import { AppHeader } from './components/AppHeader'
import { AuthScreen } from './components/AuthScreen'
import { LiveTrivia } from './components/LiveTrivia'
import { MasterAssignment } from './components/MasterAssignment'
import { PlatformAdminPanel } from './components/PlatformAdminPanel'
import { TeamAdministration } from './components/TeamAdministration'
import { TriviaBuilder } from './components/TriviaBuilder'
import { UserManagement } from './components/UserManagement'
import { addDays, formatDate } from './utils/dates'

export default function App() {
  const today = useMemo(() => formatDate(new Date()), [])
  const [authMode, setAuthMode] = useState('login')
  const [authStep, setAuthStep] = useState('request')
  const [authEmail, setAuthEmail] = useState('')
  const [authUsername, setAuthUsername] = useState('')
  const [authFirstName, setAuthFirstName] = useState('')
  const [authLastName, setAuthLastName] = useState('')
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
  const [newMembership, setNewMembership] = useState({ user_id: '', role: 'member' })
  const [teamAnalytics, setTeamAnalytics] = useState(null)
  const [notifications, setNotifications] = useState([])
  const [newTeam, setNewTeam] = useState({ name: '', approval_required: true, initial_admin_id: '' })
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
    setNewMembership({ user_id: '', role: 'member' })
  }, [selectedTeamId])

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
  const selectedTeamCycles = useMemo(
    () => cycles.filter((cycle) => String(cycle.team) === String(selectedTeamId)),
    [cycles, selectedTeamId],
  )
  const availableTeamUsers = useMemo(() => {
    const memberIds = new Set(teamMembers.map((membership) => String(membership.user)))
    return users.filter((user) => !memberIds.has(String(user.id)))
  }, [teamMembers, users])
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
        ...(authMode === 'register' ? {
          username: authUsername.trim(),
          first_name: authFirstName.trim(),
          last_name: authLastName.trim(),
        } : {}),
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
      const assignedAdmin = users.find((user) => String(user.id) === String(newTeam.initial_admin_id))
      setNewTeam({ name: '', approval_required: true, initial_admin_id: '' })
      setMessage(`Created team ${team.name}${assignedAdmin ? ` with ${assignedAdmin.username} as team admin` : ''}. Invite code: ${team.invite_code}`)
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

  const handleAddTeamMember = async () => {
    try {
      const membership = await api.addTeamMember(selectedTeamId, newMembership)
      setTeamMembers((current) => [...current, membership].sort((a, b) => a.username.localeCompare(b.username)))
      setTeams((current) => current.map((team) => (
        String(team.id) === String(selectedTeamId)
          ? { ...team, member_count: team.member_count + 1 }
          : team
      )))
      setTeamAnalytics((current) => current ? { ...current, approved_members: current.approved_members + 1 } : current)
      setNewMembership({ user_id: '', role: 'member' })
      setMessage(`Added ${membership.username} to ${selectedTeam.name} as ${membership.role === 'team_admin' ? 'team admin' : 'member'}.`)
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
      const session = await api.generateTrivia(builder.cycleId, { title: builder.title })
      setCycles(await api.getMasterCycles())
      setActiveSession(session)
      setBuilder((current) => ({
        ...current,
        sessionId: String(session.id),
        title: session.title,
        questions: session.questions,
      }))
      setMessage(`AI generated and published ${session.title}. The team has 24 hours to answer.`)
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
    return <AuthScreen
      auth={{ mode: authMode, step: authStep, email: authEmail, username: authUsername, firstName: authFirstName, lastName: authLastName, code: authCode }}
      setters={{ setMode: setAuthMode, setStep: setAuthStep, setEmail: setAuthEmail, setUsername: setAuthUsername, setFirstName: setAuthFirstName, setLastName: setAuthLastName, setCode: setAuthCode }}
      message={message}
      onRequestCode={handleRequestCode}
      onVerifyCode={handleVerifyCode}
    />
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
      <AppHeader currentView={dashboardView} isPlatformAdmin={createdUser.is_staff} onViewChange={setDashboardView} />

      <Box className="app-shell" sx={{ py: 4, minHeight: '100vh' }}>
        <Container maxWidth="lg">
          <Box className="hero-panel" sx={{ color: 'white', mb: 4 }}>
            <Typography variant="overline" letterSpacing={4}>
              ✦ Biweekly trivia battles ✦
            </Typography>
            <Typography variant="h2" fontWeight={900} sx={{ maxWidth: 760 }}>
              Big questions. Bright ideas. <span className="hero-pop">Bragging rights.</span>
            </Typography>
            <Typography sx={{ maxWidth: 680, mt: 1.5, fontSize: { xs: '1rem', md: '1.15rem' } }}>
              Play master-approved trivia with your team and turn every clever answer into a trophy.
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
                    <Chip
                      label={`Signed in: ${[createdUser.first_name, createdUser.last_name].filter(Boolean).join(' ') || createdUser.username}`}
                      color="success"
                    />
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
                          {team.name} ({team.approval_required ? 'approval required' : 'approved'})
                        </MenuItem>
                      ))}
                    </TextField>
                    <TextField label="Invite code" value={inviteCode} onChange={(event) => setInviteCode(event.target.value)} fullWidth />
                    <Button variant="outlined" onClick={handleJoinTeam} disabled={!inviteCode.trim()} sx={{ minWidth: 120 }}>Join team</Button>
                  </Stack>
                  {selectedTeam ? (
                    <Alert severity={selectedTeam.approval_required ? 'warning' : 'success'}>
                      {selectedTeam.name} · {selectedTeam.member_count} members
                      {selectedTeam.approval_required ? ' · New members require approval' : ' · New members are approved immediately'}
                      {canManageSelectedTeam ? ` · Invite code: ${selectedTeam.invite_code}` : ''}
                    </Alert>
                  ) : <Typography color="text.secondary">Join a team to access its trivia.</Typography>}
                </CardContent>
              </Card>
            </Grid>

            {createdUser.is_staff && dashboardView === 'admin' ? (
              <PlatformAdminPanel
                currentUser={createdUser}
                users={users}
                team={newTeam}
                setTeam={setNewTeam}
                onCreateTeam={handleCreateTeam}
                onToggleAdmin={handleAdminToggle}
              />
            ) : null}

            {canManageSelectedTeam ? (
              <TeamAdministration
                currentUser={createdUser}
                teams={teams}
                selectedTeam={selectedTeam}
                selectedTeamId={selectedTeamId}
                setSelectedTeamId={setSelectedTeamId}
                cycles={selectedTeamCycles}
                analytics={teamAnalytics}
                members={teamMembers}
                availableUsers={availableTeamUsers}
                newMembership={newMembership}
                setNewMembership={setNewMembership}
                onAddMember={handleAddTeamMember}
                onUpdateMember={handleMembershipUpdate}
                onRemoveMember={handleRemoveMembership}
              />
            ) : null}

            {canManageSelectedTeam ? (
              <MasterAssignment
                team={selectedTeam}
                members={teamMembers}
                cycle={masterCycle}
                setCycle={setMasterCycle}
                onCreate={handleCreateMasterCycle}
              />
            ) : null}

            {createdUser.is_staff && dashboardView === 'admin' ? (
              <UserManagement
                currentUser={createdUser}
                users={users}
                username={managedUsername}
                setUsername={setManagedUsername}
                email={managedEmail}
                setEmail={setManagedEmail}
                onAdd={handleMasterAddUser}
                onRemove={handleRemoveUser}
              />
            ) : null}

            <TriviaBuilder
              builder={builder}
              cycles={manageableCycles}
              setBuilder={setBuilder}
              onLoadDraft={handleLoadDraft}
              onAddQuestion={handleAddQuestion}
              onSave={handleCreateTrivia}
              onGenerate={handleGenerateTrivia}
            />
            <LiveTrivia
              session={activeSession}
              questions={activeQuestions}
              choices={selectedChoices}
              setChoices={setSelectedChoices}
              canManage={canManageActiveSession}
              onSubmit={handleSubmitAnswer}
              onPublish={handlePublishSession}
              onEvaluate={handleEvaluateSession}
            />
          </Grid>
        </Container>
      </Box>
    </>
  )
}
