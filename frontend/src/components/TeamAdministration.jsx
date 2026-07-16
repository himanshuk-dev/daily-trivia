import { Alert, Box, Button, Card, CardContent, Chip, Grid, List, ListItem, ListItemText, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material'

export function TeamAdministration({
  currentUser,
  teams,
  selectedTeam,
  selectedTeamId,
  setSelectedTeamId,
  cycles,
  analytics,
  members,
  availableUsers,
  newMembership,
  setNewMembership,
  onAddMember,
  onUpdateMember,
  onRemoveMember,
  onEditTeam,
  onToggleTeamApproval,
  onDeleteTeam,
}) {
  if (!selectedTeam) return null

  return (
    <Grid item xs={12}>
      <Card sx={{ borderRadius: 4 }}><CardContent>
        <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2} sx={{ mb: 2 }}>
          <Box>
            <Typography variant="h6">Team administration</Typography>
            <Typography color="text.secondary">Review each team’s administrators, masters, members, admission policy, and activity.</Typography>
          </Box>
          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
            <Chip color={selectedTeam.approval_required ? 'warning' : 'success'} label={selectedTeam.approval_required ? 'Approval required' : 'Immediate approval'} />
            {currentUser.is_staff ? <Button size="small" variant="outlined" onClick={() => onEditTeam(selectedTeam)}>Edit name</Button> : null}
            {currentUser.is_staff ? <Button size="small" variant="outlined" onClick={() => onToggleTeamApproval(selectedTeam)}>{selectedTeam.approval_required ? 'Allow immediate join' : 'Require approval'}</Button> : null}
            {currentUser.is_staff ? <Button size="small" variant="outlined" color="error" onClick={() => onDeleteTeam(selectedTeam)}>Delete team</Button> : null}
          </Stack>
        </Stack>

        {currentUser.is_staff ? (
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>All teams</Typography>
            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
              {teams.map((team) => (
                <Button key={team.id} size="small" variant={String(team.id) === String(selectedTeamId) ? 'contained' : 'outlined'} onClick={() => setSelectedTeamId(String(team.id))}>
                  {team.name} · {team.member_count} members
                </Button>
              ))}
            </Stack>
          </Box>
        ) : null}

        <Paper variant="outlined" sx={{ p: 2.5, mb: 3, borderRadius: 3, bgcolor: '#fbf8ff' }}>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <Typography variant="caption" color="text.secondary">Team</Typography>
              <Typography fontWeight={900}>{selectedTeam.name}</Typography>
              <Typography variant="body2" color="text.secondary">/{selectedTeam.slug}</Typography>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Typography variant="caption" color="text.secondary">Created by</Typography>
              <Typography fontWeight={800}>{selectedTeam.created_by_username || `User #${selectedTeam.created_by}`}</Typography>
              <Typography variant="body2" color="text.secondary">{new Date(selectedTeam.created_at).toLocaleDateString()}</Typography>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Typography variant="caption" color="text.secondary">Invite code</Typography>
              <Typography fontWeight={900}>{selectedTeam.invite_code || 'Hidden'}</Typography>
              <Typography variant="body2" color="text.secondary">{selectedTeam.approval_required ? 'Admin reviews new members' : 'Members join approved'}</Typography>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Typography variant="caption" color="text.secondary">Activity</Typography>
              <Typography fontWeight={900}>{cycles.length} cycles</Typography>
              <Typography variant="body2" color="text.secondary">{analytics?.trivia_sessions ?? 0} sessions · {analytics?.trophies ?? 0} trophies</Typography>
            </Grid>
          </Grid>
        </Paper>

        {analytics ? <Alert severity="info" sx={{ mb: 2 }}>{analytics.approved_members} members · {analytics.pending_members} pending · {analytics.trivia_sessions} sessions · {analytics.answers} answers · {analytics.trophies} trophies</Alert> : null}

        <Typography variant="subtitle1" fontWeight={900} sx={{ mt: 3 }}>Masters and cycles</Typography>
        {cycles.length === 0 ? <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>No master has been assigned to a cycle for this team.</Typography> : (
          <Grid container spacing={2} sx={{ mb: 3, mt: 0 }}>
            {cycles.map((cycle) => (
              <Grid item xs={12} md={6} key={cycle.id}>
                <Paper variant="outlined" sx={{ p: 2, borderRadius: 3, height: '100%' }}>
                  <Stack direction="row" justifyContent="space-between" spacing={1} alignItems="flex-start">
                    <Box><Typography variant="caption" color="text.secondary">Master</Typography><Typography fontWeight={900}>{cycle.master_name}</Typography></Box>
                    <Chip size="small" label={cycle.status} color={cycle.status === 'active' ? 'success' : 'default'} />
                  </Stack>
                  <Typography sx={{ mt: 1 }}><strong>Topic:</strong> {cycle.topic}</Typography>
                  <Typography variant="body2" color="text.secondary">{cycle.start_date} to {cycle.end_date} · {cycle.trivia_sessions?.length ?? 0} sessions</Typography>
                  {cycle.sprint_leaderboard?.length ? (
                    <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1.5 }}>
                      {cycle.sprint_leaderboard.map((entry, index) => (
                        <Chip key={entry.user_id} size="small" color={index === 0 ? 'warning' : 'default'} label={`#${index + 1} ${entry.username} · 🏆 ${entry.trophy_count}`} />
                      ))}
                    </Stack>
                  ) : <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>Sprint leaderboard begins after trophies are awarded.</Typography>}
                </Paper>
              </Grid>
            ))}
          </Grid>
        )}

        <Typography variant="subtitle1" fontWeight={900}>People and roles</Typography>
        <Paper variant="outlined" sx={{ p: 2, my: 1.5, borderRadius: 3, bgcolor: '#fbf8ff' }}>
          <Typography variant="subtitle2" sx={{ mb: 1.5 }}>Add an existing user</Typography>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
            <TextField select fullWidth label="User" value={newMembership.user_id} onChange={(event) => setNewMembership((current) => ({ ...current, user_id: event.target.value }))}>
              {availableUsers.length === 0 ? <MenuItem value="" disabled>All active users are already on this team</MenuItem> : availableUsers.map((user) => (
                <MenuItem key={user.id} value={String(user.id)}>{[user.first_name, user.last_name].filter(Boolean).join(' ') || user.username} · {user.email}</MenuItem>
              ))}
            </TextField>
            <TextField select label="Team role" value={newMembership.role} onChange={(event) => setNewMembership((current) => ({ ...current, role: event.target.value }))} sx={{ minWidth: { md: 220 } }}>
              <MenuItem value="member">Member</MenuItem><MenuItem value="team_admin">Team admin</MenuItem>
            </TextField>
            <Button variant="contained" onClick={onAddMember} disabled={!newMembership.user_id} sx={{ minWidth: 150 }}>Add to team</Button>
          </Stack>
          <Typography variant="caption" color="text.secondary">Directly added users are approved immediately. They can access this team the next time their dashboard refreshes.</Typography>
        </Paper>

        <List disablePadding>{members.map((membership) => (
          <ListItem key={membership.id} disableGutters divider sx={{ py: 1.5, alignItems: { xs: 'flex-start', md: 'center' }, flexDirection: { xs: 'column', md: 'row' }, gap: 1 }}>
            <ListItemText primary={[membership.first_name, membership.last_name].filter(Boolean).join(' ') || membership.username} secondary={`${membership.username} · ${membership.email}`} sx={{ minWidth: 240 }} />
            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ flex: 1 }}>
              <Chip size="small" color={membership.role === 'team_admin' ? 'primary' : 'default'} label={membership.role === 'team_admin' ? 'Team admin' : 'Member'} />
              <Chip size="small" color={membership.status === 'approved' ? 'success' : membership.status === 'pending' ? 'warning' : 'error'} label={membership.status} />
              {cycles.filter((cycle) => cycle.master_name === membership.username).map((cycle) => <Chip key={cycle.id} size="small" color="warning" label={`Master · ${cycle.topic}`} />)}
            </Stack>
            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
              {membership.status === 'pending' ? <><Button size="small" onClick={() => onUpdateMember(membership, { status: 'approved' })}>Approve</Button><Button size="small" color="error" onClick={() => onUpdateMember(membership, { status: 'rejected' })}>Reject</Button></> : null}
              {membership.status === 'approved' && membership.user !== currentUser.id ? <Button size="small" onClick={() => onUpdateMember(membership, { role: membership.role === 'team_admin' ? 'member' : 'team_admin' })}>{membership.role === 'team_admin' ? 'Make member' : 'Make team admin'}</Button> : null}
              {membership.user !== currentUser.id ? <Button size="small" color="error" onClick={() => onRemoveMember(membership)}>Remove</Button> : null}
            </Stack>
          </ListItem>
        ))}</List>
      </CardContent></Card>
    </Grid>
  )
}
