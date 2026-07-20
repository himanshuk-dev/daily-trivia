import GitHubIcon from '@mui/icons-material/GitHub'
import { Box, Link, Typography } from '@mui/material'

const repositoryUrl = 'https://github.com/himanshuk-dev/daily-trivia'

export function SiteFooter() {
  return (
    <Box component="footer" sx={{ mt: 5, pb: 1, textAlign: 'center' }}>
      <Link
        href={repositoryUrl}
        target="_blank"
        rel="noopener noreferrer"
        color="inherit"
        underline="hover"
        sx={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 1,
          color: 'white',
          fontWeight: 700,
        }}
      >
        <GitHubIcon fontSize="small" />
        himanshuk-dev/daily-trivia
      </Link>
      <Typography variant="body2" sx={{ mt: 1, color: 'rgba(255, 255, 255, 0.85)' }}>
        Report issues or suggest features under{' '}
        <Link
          href={`${repositoryUrl}/issues`}
          target="_blank"
          rel="noopener noreferrer"
          color="inherit"
          fontWeight={800}
        >
          Issues
        </Link>{' '}
        on GitHub.
      </Typography>
    </Box>
  )
}
