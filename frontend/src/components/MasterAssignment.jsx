import { Button, Card, CardContent, Grid, MenuItem, TextField, Typography } from '@mui/material'
import { addDays } from '../utils/dates'

export function MasterAssignment({ team, members, cycle, setCycle, onCreate }) {
  return (
    <Grid item xs={12}><Card sx={{ borderRadius: 4 }}><CardContent>
      <Typography variant="h6" gutterBottom>Add master</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Select an approved {team?.name} member to lead the next two-week trivia cycle.</Typography>
      <Grid container spacing={2}>
        <Grid item xs={12} md={3}>
          <TextField select fullWidth label="Master" value={cycle.master_username} onChange={(event) => setCycle((current) => ({ ...current, master_username: event.target.value }))} disabled={!members.length}>
            {members.filter((membership) => membership.status === 'approved').map((membership) => <MenuItem key={membership.user} value={membership.username}>{membership.username}</MenuItem>)}
          </TextField>
        </Grid>
        <Grid item xs={12} md={3}><TextField fullWidth label="Sprint name" value={cycle.topic} onChange={(event) => setCycle((current) => ({ ...current, topic: event.target.value }))} /></Grid>
        <Grid item xs={12} sm={6} md={2}>
          <TextField fullWidth type="date" label="Start date" InputLabelProps={{ shrink: true }} value={cycle.start_date} onChange={(event) => setCycle((current) => ({ ...current, start_date: event.target.value, end_date: addDays(event.target.value, 13) }))} />
        </Grid>
        <Grid item xs={12} sm={6} md={2}><TextField fullWidth type="date" label="End date" InputLabelProps={{ shrink: true }} value={cycle.end_date} onChange={(event) => setCycle((current) => ({ ...current, end_date: event.target.value }))} /></Grid>
        <Grid item xs={12} md={2}><Button fullWidth variant="contained" sx={{ height: '100%' }} onClick={onCreate} disabled={!cycle.master_username || !cycle.topic.trim()}>Create sprint</Button></Grid>
        <Grid item xs={12}><Typography variant="body2" color="text.secondary">The master chooses that day’s trivia topic when generating the question. All trophies count toward this two-week sprint.</Typography></Grid>
      </Grid>
    </CardContent></Card></Grid>
  )
}
