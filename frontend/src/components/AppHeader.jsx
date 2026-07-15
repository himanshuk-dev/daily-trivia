import EmojiEventsIcon from '@mui/icons-material/EmojiEvents'
import { AppBar, Box, Button, Stack, Toolbar, Typography } from '@mui/material'

export function AppHeader({ currentView, isPlatformAdmin, onViewChange }) {
  return (
    <AppBar position="sticky" className="trivia-appbar" elevation={0}>
      <Toolbar sx={{ justifyContent: 'space-between' }}>
        <Stack direction="row" spacing={1} alignItems="center">
          <Box className="mini-mark"><EmojiEventsIcon /></Box>
          <Typography variant="h6">Daily <span className="orange-word">Trivia</span></Typography>
        </Stack>
        <Stack direction="row" spacing={1}>
          <Button variant={currentView === 'user' ? 'contained' : 'text'} onClick={() => onViewChange('user')}>User dashboard</Button>
          {isPlatformAdmin ? (
            <Button variant={currentView === 'admin' ? 'contained' : 'text'} onClick={() => onViewChange('admin')}>Admin dashboard</Button>
          ) : null}
        </Stack>
      </Toolbar>
    </AppBar>
  )
}
