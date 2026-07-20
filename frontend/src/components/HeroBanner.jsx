import { Box, Typography } from '@mui/material'

export function HeroBanner() {
  return (
    <Box className="hero-panel" sx={{ color: 'white', mb: 4 }}>
      <Typography variant="overline" letterSpacing={4}>✦ Biweekly trivia battles ✦</Typography>
      <Typography variant="h2" fontWeight={900} sx={{ maxWidth: 760 }}>
        Big questions. Bright ideas. <span className="hero-pop">Bragging rights.</span>
      </Typography>
      <Typography sx={{ maxWidth: 680, mt: 1.5, fontSize: { xs: '1rem', md: '1.15rem' } }}>
        Play master-approved trivia with your team and turn every clever answer into a trophy.
      </Typography>
    </Box>
  )
}
