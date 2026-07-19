import EmojiEventsIcon from '@mui/icons-material/EmojiEvents'
import { Card, CardContent, Chip, Grid, Paper, Stack, Typography } from '@mui/material'

export function LeaderboardCard({ leaderboard }) {
  return (
    <Grid item xs={12} md={4}>
      <Card sx={{ borderRadius: 4, height: '100%' }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Public leaderboard</Typography>
          <Stack spacing={1}>
            {leaderboard.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                Leaderboard appears after correct answers are evaluated.
              </Typography>
            ) : (
              leaderboard.map((entry, index) => (
                <Paper key={entry.user_id} variant="outlined" sx={{ p: 1.5, borderRadius: 3 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Typography fontWeight={700}>#{index + 1} {entry.username}</Typography>
                    <Chip
                      icon={<EmojiEventsIcon />}
                      label={entry.trophy_count}
                      color="warning"
                      aria-label={`${entry.trophy_count} ${entry.trophy_count === 1 ? 'trophy' : 'trophies'}`}
                      sx={{ fontWeight: 800 }}
                    />
                  </Stack>
                </Paper>
              ))
            )}
          </Stack>
        </CardContent>
      </Card>
    </Grid>
  )
}
