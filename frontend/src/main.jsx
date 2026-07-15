import React from 'react'
import ReactDOM from 'react-dom/client'
import { createTheme, ThemeProvider } from '@mui/material/styles'
import App from './App'
import './styles.css'

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#5420c7', dark: '#35108f', contrastText: '#ffffff' },
    secondary: { main: '#ff5bbd', dark: '#d73593', contrastText: '#25103d' },
    warning: { main: '#ffb12b', dark: '#f47420', contrastText: '#25103d' },
    success: { main: '#7f48ff', dark: '#5420c7', contrastText: '#ffffff' },
    info: { main: '#8a4dff', dark: '#5420c7', contrastText: '#ffffff' },
    background: { default: '#fff8fd', paper: '#ffffff' },
    text: { primary: '#25103d', secondary: '#6b5680' },
  },
  shape: { borderRadius: 18 },
  typography: {
    fontFamily: '"Arial Rounded MT Bold", "Avenir Next", Inter, system-ui, sans-serif',
    h2: { fontWeight: 900, letterSpacing: '-0.045em' },
    h4: { fontWeight: 900, letterSpacing: '-0.035em' },
    h6: { fontWeight: 900 },
    button: { fontWeight: 900, letterSpacing: '0.01em', textTransform: 'none' },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: 999, paddingInline: 20, minHeight: 42 },
        contained: {
          boxShadow: '0 5px 0 #35108f',
          '&:hover': { boxShadow: '0 3px 0 #35108f', transform: 'translateY(2px)' },
          '&:active': { boxShadow: 'none', transform: 'translateY(5px)' },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: { border: '2px solid #eadcff', boxShadow: '0 12px 30px rgba(84, 32, 199, 0.12)' },
      },
    },
    MuiTextField: { defaultProps: { variant: 'outlined' } },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          backgroundColor: '#fff',
          '& fieldset': { borderColor: '#d9c5ff', borderWidth: 2 },
          '&:hover fieldset': { borderColor: '#8a4dff' },
          '&.Mui-focused fieldset': { borderColor: '#5420c7', borderWidth: 2 },
        },
      },
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <App />
    </ThemeProvider>
  </React.StrictMode>,
)
