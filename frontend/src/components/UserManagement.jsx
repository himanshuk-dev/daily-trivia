import { Button, Card, CardContent, Grid, List, ListItem, ListItemText, Stack, TextField, Typography } from '@mui/material'

export function UserManagement({ currentUser, users, username, setUsername, email, setEmail, onAdd, onRemove }) {
  return (
    <Grid item xs={12}><Card sx={{ borderRadius: 4 }}><CardContent>
      <Typography variant="h6" gutterBottom>Platform user management</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Invite new accounts by email or remove accounts that have no protected master-cycle history.</Typography>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
        <TextField label="New username" value={username} onChange={(event) => setUsername(event.target.value)} fullWidth />
        <TextField label="Email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} fullWidth />
        <Button variant="contained" onClick={onAdd} disabled={!username.trim() || !email.trim()} sx={{ minWidth: 140 }}>Add user</Button>
      </Stack>
      <List disablePadding>{users.map((user) => (
        <ListItem key={user.id} disableGutters secondaryAction={<Button color="error" onClick={() => onRemove(user)} disabled={user.id === currentUser.id}>Remove</Button>}>
          <ListItemText primary={user.username} secondary={user.id === currentUser.id ? 'Current user' : user.email} />
        </ListItem>
      ))}</List>
    </CardContent></Card></Grid>
  )
}
