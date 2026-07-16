import EmojiEventsIcon from '@mui/icons-material/EmojiEvents'
import {
  Accordion, AccordionDetails, AccordionSummary, Alert, Box, Button, Card, CardContent,
  Chip, Grid, Paper, Stack, Typography,
} from '@mui/material'

export function PlatformOverview({ overview, onRefresh }) {
  if (!overview) return null

  return (
    <Grid item xs={12}>
      <Card sx={{ borderRadius: 4 }}><CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2} sx={{ mb: 2 }}>
          <Box>
            <Typography variant="h6">Platform activity overview</Typography>
            <Typography color="text.secondary">All teams, people, trivia participation, and leaderboards.</Typography>
          </Box>
          <Button variant="outlined" onClick={onRefresh}>Refresh</Button>
        </Stack>

        <Grid container spacing={2} sx={{ mb: 3 }}>
          {[
            ['Teams', overview.team_count], ['People', overview.user_count],
            ['Trivia sessions', overview.trivia_count], ['Answers', overview.answer_count],
          ].map(([label, value]) => (
            <Grid item xs={6} md={3} key={label}>
              <Paper variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
                <Typography variant="h4" fontWeight={900}>{value}</Typography>
                <Typography color="text.secondary">{label}</Typography>
              </Paper>
            </Grid>
          ))}
        </Grid>

        {overview.teams.length === 0 ? <Alert severity="info">No teams have been created.</Alert> : overview.teams.map((team) => (
          <Accordion key={team.id} disableGutters sx={{ mb: 1.5, borderRadius: '16px !important', overflow: 'hidden' }}>
            <AccordionSummary>
              <Box sx={{ width: '100%' }}>
                <Typography fontWeight={900}>{team.name}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {team.members.length} people · {team.trivia_sessions.length} trivia sessions · {team.leaderboard.length} ranked players
                </Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Typography fontWeight={900} sx={{ mb: 1 }}>People</Typography>
              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mb: 3 }}>
                {team.members.map((member) => (
                  <Chip key={member.id} label={`${member.username} · ${member.role === 'team_admin' ? 'Team admin' : 'Member'} · ${member.status}`} color={member.role === 'team_admin' ? 'primary' : member.status === 'approved' ? 'success' : 'default'} variant="outlined" />
                ))}
              </Stack>

              <Typography fontWeight={900} sx={{ mb: 1 }}>Trivia and participation</Typography>
              <Stack spacing={1.5} sx={{ mb: 3 }}>
                {team.trivia_sessions.length === 0 ? <Typography color="text.secondary">No trivia sessions.</Typography> : team.trivia_sessions.map((session) => (
                  <Paper key={session.id} variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
                    <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={1}>
                      <Box>
                        <Typography fontWeight={900}>{session.title}</Typography>
                        <Typography variant="body2" color="text.secondary">{session.topic} · Master: {session.master} · {session.status}</Typography>
                      </Box>
                      <Typography variant="body2" color="text.secondary">{session.close_at ? `Closes ${new Date(session.close_at).toLocaleString()}` : 'No deadline'}</Typography>
                    </Stack>
                    <Typography variant="subtitle2" sx={{ mt: 1.5 }}>Answered by</Typography>
                    {session.submissions.length === 0 ? <Typography variant="body2" color="text.secondary">No submissions</Typography> : (
                      <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                        {session.submissions.map((submission) => <Chip key={submission.user_id} size="small" label={`${submission.username} · ${submission.answers_submitted} answered`} />)}
                      </Stack>
                    )}
                  </Paper>
                ))}
              </Stack>

              <Typography fontWeight={900} sx={{ mb: 1 }}>Leaderboard</Typography>
              {team.leaderboard.length === 0 ? <Typography color="text.secondary">No trophies awarded.</Typography> : (
                <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                  {team.leaderboard.map((entry, index) => (
                    <Chip key={entry.user_id} icon={<EmojiEventsIcon />} color="warning" label={`#${index + 1} ${entry.username} · ${entry.trophy_count}`} />
                  ))}
                </Stack>
              )}
            </AccordionDetails>
          </Accordion>
        ))}
      </CardContent></Card>
    </Grid>
  )
}
