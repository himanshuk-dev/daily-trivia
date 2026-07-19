import { Box, Button, Card, CardContent, Divider, Grid, List, ListItem, ListItemText, Typography } from '@mui/material'

export function CurrentCyclesCard({ cycles, onLoadTrivia }) {
  return (
    <Grid item xs={12} md={4}>
      <Card sx={{ borderRadius: 4, height: '100%' }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Current cycles</Typography>
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
                  {cycle.sprint_winner ? (
                    <Typography variant="body2" color="warning.dark" fontWeight={800}>
                      {cycle.status === 'closed' ? 'Cycle winner' : 'Cycle leader'}: {cycle.sprint_winner.username} · 🏆 {cycle.sprint_winner.trophy_count}
                    </Typography>
                  ) : null}
                  <Divider sx={{ my: 1 }} />
                </Box>
              ))
            )}
          </List>
          <Button sx={{ mt: 1 }} variant="outlined" onClick={onLoadTrivia}>
            Load current or latest trivia
          </Button>
        </CardContent>
      </Card>
    </Grid>
  )
}
