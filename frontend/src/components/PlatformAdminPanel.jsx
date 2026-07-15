import { Button, Card, CardContent, Grid, List, ListItem, ListItemText, MenuItem, Stack, TextField, Typography } from '@mui/material'

export function PlatformAdminPanel({ currentUser, users, team, setTeam, onCreateTeam, onToggleAdmin }) {
  return (
    <Grid item xs={12}><Card sx={{ borderRadius: 4 }}><CardContent>
      <Typography variant="h6" gutterBottom>Platform admin dashboard</Typography>
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mb: 2 }}>
        <TextField label="New team name" value={team.name} onChange={(event) => setTeam((current) => ({ ...current, name: event.target.value }))} fullWidth />
        <TextField select label="Initial team admin" value={team.initial_admin_id} onChange={(event) => setTeam((current) => ({ ...current, initial_admin_id: event.target.value }))} fullWidth>
          <MenuItem value="">Assign me</MenuItem>
          {users.map((user) => <MenuItem key={user.id} value={String(user.id)}>{[user.first_name, user.last_name].filter(Boolean).join(' ') || user.username} ({user.username})</MenuItem>)}
        </TextField>
        <TextField select label="Membership approval" value={String(team.approval_required)} onChange={(event) => setTeam((current) => ({ ...current, approval_required: event.target.value === 'true' }))} fullWidth>
          <MenuItem value="true">Admin approval required</MenuItem><MenuItem value="false">Join immediately</MenuItem>
        </TextField>
        <Button variant="contained" onClick={onCreateTeam} disabled={!team.name.trim()} sx={{ minWidth: 140 }}>Create team</Button>
      </Stack>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>The initial admin is approved automatically and can assign themselves or another approved member as trivia master.</Typography>
      <Typography variant="subtitle2">Platform administrators</Typography>
      <List dense>{users.map((user) => (
        <ListItem key={user.id} disableGutters secondaryAction={<Button onClick={() => onToggleAdmin(user)} disabled={user.id === currentUser.id}>{user.is_staff ? 'Remove admin' : 'Make admin'}</Button>}>
          <ListItemText primary={user.username} secondary={`${user.email}${user.is_staff ? ' · Admin' : ''}`} />
        </ListItem>
      ))}</List>
    </CardContent></Card></Grid>
  )
}
