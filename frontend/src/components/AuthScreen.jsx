import { Alert, Box, Button, Card, CardContent, CssBaseline, Stack, TextField, Typography } from '@mui/material'

export function AuthScreen({ auth, setters, message, onRequestCode, onVerifyCode }) {
  const { mode, step, email, username, firstName, lastName, code } = auth
  const { setMode, setStep, setEmail, setUsername, setFirstName, setLastName, setCode } = setters
  const registrationIncomplete = !firstName.trim() || !lastName.trim() || !username.trim()

  return (
    <>
      <CssBaseline />
      <Box className="auth-shell" sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', p: 2 }}>
        <Card className="auth-card" sx={{ width: '100%', maxWidth: 500, borderRadius: 4 }}>
          <CardContent sx={{ p: 4 }}>
            <Stack spacing={3}>
              <Box>
                <Box className="trivia-mark" aria-hidden="true">?</Box>
                <Typography variant="overline" className="eyebrow">Ready, set, think!</Typography>
                <Typography variant="h4">Daily <span className="orange-word">Trivia</span></Typography>
                <Typography color="text.secondary">Join the fun with a one-time email code. No passwords, no fuss.</Typography>
              </Box>
              {message ? <Alert severity="info">{message}</Alert> : null}
              {step === 'request' ? (
                <>
                  <Stack direction="row" spacing={1}>
                    <Button variant={mode === 'login' ? 'contained' : 'outlined'} onClick={() => setMode('login')}>Login</Button>
                    <Button variant={mode === 'register' ? 'contained' : 'outlined'} onClick={() => setMode('register')}>Register</Button>
                  </Stack>
                  {mode === 'register' ? (
                    <>
                      <TextField label="First name" value={firstName} onChange={(event) => setFirstName(event.target.value)} required />
                      <TextField label="Last name" value={lastName} onChange={(event) => setLastName(event.target.value)} required />
                      <TextField label="Username" value={username} onChange={(event) => setUsername(event.target.value)} required />
                    </>
                  ) : null}
                  <TextField label="Email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
                  <Button variant="contained" onClick={onRequestCode} disabled={!email.trim() || (mode === 'register' && registrationIncomplete)}>
                    Email me a code
                  </Button>
                </>
              ) : (
                <>
                  <TextField label="Six-digit code" value={code} onChange={(event) => setCode(event.target.value)} inputProps={{ maxLength: 6 }} />
                  <Button variant="contained" onClick={onVerifyCode} disabled={code.trim().length !== 6}>Verify and continue</Button>
                  <Button onClick={() => setStep('request')}>Use a different email</Button>
                </>
              )}
            </Stack>
          </CardContent>
        </Card>
      </Box>
    </>
  )
}
