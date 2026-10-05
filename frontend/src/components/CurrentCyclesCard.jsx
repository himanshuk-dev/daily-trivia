import { useState } from 'react'
import { Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Divider, Grid, List, ListItem, ListItemText, Stack, Typography } from '@mui/material'

export function CurrentCyclesCard({ cycles, teams = [], showTeamTags = false, onLoadTrivia }) {
  const [historyOpen, setHistoryOpen] = useState(false)
  const sortedCycles = [...cycles].sort((a, b) => (
    b.start_date.localeCompare(a.start_date)
    || b.end_date.localeCompare(a.end_date)
    || Number(b.id) - Number(a.id)
  ))
  const projectCounts = new Map()
  const recentCycles = sortedCycles.filter((cycle) => {
    const project = String(cycle.team ?? 'unassigned')
    const count = projectCounts.get(project) || 0
    projectCounts.set(project, count + 1)
    return count < 2
  })

  function renderCycles(items) {
    return items.map((cycle) => (
      <Box component="li" key={cycle.id} sx={{ mb: 2, listStyle: 'none' }}>
        <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap">
          <Typography fontWeight={700}>{cycle.topic}</Typography>
          {showTeamTags ? (
            <Chip
              size="small"
              variant="outlined"
              color="primary"
              label={teams.find((team) => String(team.id) === String(cycle.team))?.name || 'Unknown team'}
            />
          ) : null}
        </Stack>
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
  }

  return (
    <Grid item xs={12} md={4}>
      <Card sx={{ borderRadius: 4, height: '100%' }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Current cycles</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Latest two sprints per project
          </Typography>
          <List dense disablePadding>
            {cycles.length === 0 ? (
              <ListItem disableGutters>
                <ListItemText primary="No cycles yet" secondary="Use the Add master form below." />
              </ListItem>
            ) : (
              renderCycles(recentCycles)
            )}
          </List>
          <Button sx={{ mt: 1, mr: 1 }} variant="text" onClick={() => setHistoryOpen(true)} disabled={cycles.length === 0}>
            View sprint history
          </Button>
          <Button sx={{ mt: 1 }} variant="outlined" onClick={onLoadTrivia}>
            Load current or latest trivia
          </Button>
        </CardContent>
      </Card>
      <Dialog open={historyOpen} onClose={() => setHistoryOpen(false)} fullWidth maxWidth="sm" scroll="paper" aria-labelledby="sprint-history-title">
        <DialogTitle id="sprint-history-title">Sprint history</DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            All sprints, newest first
          </Typography>
          <List dense disablePadding>{renderCycles(sortedCycles)}</List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setHistoryOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Grid>
  )
}
