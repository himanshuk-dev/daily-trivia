import { useEffect, useState } from 'react'
import EditIcon from '@mui/icons-material/Edit'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  IconButton,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'

export function AccountCard({
  user,
  teams,
  cycles,
  notifications,
  onUpdateUsername,
  onMarkNotificationsRead,
  onLogout,
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [username, setUsername] = useState(user.username)
  const [isSaving, setIsSaving] = useState(false)
  const unreadNotifications = notifications.filter((item) => !item.read_at)

  useEffect(() => {
    setUsername(user.username)
  }, [user.username])

  const saveUsername = async () => {
    const nextUsername = username.trim()
    if (!nextUsername || nextUsername === user.username) {
      setUsername(user.username)
      setIsEditing(false)
      return
    }

    setIsSaving(true)
    const saved = await onUpdateUsername(nextUsername)
    setIsSaving(false)
    if (saved) setIsEditing(false)
  }

  const cancelEditing = () => {
    setUsername(user.username)
    setIsEditing(false)
  }

  return (
    <Grid item xs={12} md={4}>
      <Card sx={{ borderRadius: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Your account</Typography>
          <Stack spacing={2}>
            <Chip
              label={`Signed in: ${[user.first_name, user.last_name].filter(Boolean).join(' ') || user.username}`}
              color="success"
            />
            <Typography variant="body2" color="text.secondary">{user.email}</Typography>
            {isEditing ? (
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                <TextField
                  size="small"
                  label="Username"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  inputProps={{ maxLength: 150 }}
                  fullWidth
                />
                <Button variant="contained" onClick={saveUsername} disabled={isSaving || !username.trim()}>
                  {isSaving ? 'Saving…' : 'Save'}
                </Button>
                <Button onClick={cancelEditing} disabled={isSaving}>Cancel</Button>
              </Stack>
            ) : (
              <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
                <Typography variant="body2">Username: <strong>{user.username}</strong></Typography>
                <Tooltip title="Edit username">
                  <IconButton
                    size="small"
                    onClick={() => setIsEditing(true)}
                    aria-label="Edit username"
                  >
                    <EditIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Stack>
            )}
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>Roles</Typography>
              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                {user.is_staff ? <Chip label="Platform admin" color="primary" /> : null}
                {teams.filter((team) => team.membership_role || team.membership_status).map((team) => (
                  <Chip
                    key={team.id}
                    variant="outlined"
                    color={team.membership_status === 'pending' ? 'warning' : team.membership_status === 'rejected' ? 'error' : team.membership_role === 'team_admin' ? 'secondary' : 'default'}
                    label={`${team.name}: ${
                      team.membership_status === 'pending'
                        ? 'Pending'
                        : team.membership_status === 'rejected'
                          ? 'Rejected'
                          : team.membership_role === 'team_admin'
                            ? 'Team admin'
                            : 'Member'
                    }`}
                  />
                ))}
                {cycles.filter((cycle) => cycle.master_name === user.username && cycle.status === 'active').map((cycle) => (
                  <Chip key={`master-${cycle.id}`} label={`Trivia master: ${cycle.topic}`} color="warning" />
                ))}
                {!user.is_staff && teams.length === 0 ? <Chip label="No team role yet" variant="outlined" /> : null}
              </Stack>
            </Box>
            <Typography variant="body2">{unreadNotifications.length} unread notifications</Typography>
            {unreadNotifications.slice(0, 2).map((notification) => (
              <Alert key={notification.id} severity="info">{notification.message}</Alert>
            ))}
            {unreadNotifications.length ? (
              <Button size="small" onClick={onMarkNotificationsRead}>Mark read</Button>
            ) : null}
            <Button variant="outlined" onClick={onLogout}>Logout</Button>
          </Stack>
        </CardContent>
      </Card>
    </Grid>
  )
}
