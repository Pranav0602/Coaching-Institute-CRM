import React, { useState } from 'react';
import { Box, Container } from '@mui/material';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';

export const MainLayout = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', backgroundColor: 'background.default' }}>
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { sm: `calc(100% - ${sidebarOpen ? 260 : 0}px)` },
          transition: 'width 0.2s ease-in-out',
        }}
      >
        <Navbar onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />
        <Container maxWidth="xl" sx={{ mt: 3, mb: 4 }}>
          {children}
        </Container>
      </Box>
    </Box>
  );
};
