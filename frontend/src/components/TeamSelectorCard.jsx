import { Alert, Button, Card, CardContent, Grid, MenuItem, Stack, TextField, Typography } from '@mui/material'

export function TeamSelectorCard({
  teams,
  selectedTeam,
  selectedTeamId,
  inviteCode,
  canManage,
  onTeamChange,
  onInviteCodeChange,
  onJoinTeam,
}) {
  return (
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
              onChange={(event) => onTeamChange(event.target.value)}
            >
              {teams.map((team) => (
                <MenuItem key={team.id} value={String(team.id)}>
                  {team.name} ({team.approval_required ? 'approval required' : 'approved'})
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Invite code"
              value={inviteCode}
              onChange={(event) => onInviteCodeChange(event.target.value)}
              fullWidth
            />
            <Button variant="outlined" onClick={onJoinTeam} disabled={!inviteCode.trim()} sx={{ minWidth: 120 }}>
              Join team
            </Button>
          </Stack>
          {selectedTeam ? (
            <Alert severity={selectedTeam.approval_required ? 'warning' : 'success'}>
              {selectedTeam.name} · {selectedTeam.member_count} members
              {selectedTeam.approval_required ? ' · New members require approval' : ' · New members are approved immediately'}
              {canManage ? ` · Invite code: ${selectedTeam.invite_code}` : ''}
            </Alert>
          ) : <Typography color="text.secondary">Join a team to access its trivia.</Typography>}
        </CardContent>
      </Card>
    </Grid>
  )
}
