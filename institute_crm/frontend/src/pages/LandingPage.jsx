import React, { useState, useEffect } from 'react';
import { warmBackend } from '../services/api';
import {
  Box, Container, Typography, Button, Grid, Card, CardMedia, CardContent, Chip, Stack,
  Divider, Avatar, Paper, IconButton, Drawer, List, ListItem, ListItemText, AppBar, Toolbar, Menu, MenuItem, Link as MuiLink
} from '@mui/material';
import {
  CheckCircle, Verified, School, AutoGraph, Groups, WorkspacePremium, EventNote, DesignServices,
  Engineering, ElectricalServices, HomeWork, Cloud, Storage, Code, Language, SupportAgent,
  Phone, Email, LocationOn, Facebook, Instagram, LinkedIn, Menu as MenuIcon, Close, ArrowForward,
  Star, PlayCircle, Business, Factory, Memory, Build, Draw, Architecture, FindInPage, SmartToy, ReceiptLong
} from '@mui/icons-material';

/**
 * Optimized Graphix-style Landing Page adapted to Institute CRM theme
 * - Uses hotlinked Graphix assets (with lazy loading) + fallbacks
 * - Dark theme aware via MUI tokens
 * - Section anchors for SEO / scroll navigation
 * - All data mirrored from https://graphixtechnoservices.com/
 */

const IMG = {
  logo: 'https://graphixtechnoservices.com/wp-content/uploads/2023/02/graphix.jpg',
  logoSmall: 'https://graphixtechnoservices.com/wp-content/uploads/2024/03/cropped-WhatsApp-Image-2024-03-15-at-4.57.03-PM-300x204.jpeg',
  cloud: 'https://graphixtechnoservices.com/wp-content/uploads/2021/11/cloud-computing-502462262-5ac1130e119fa800371ba0a8-scaled.jpg',
  mechanical: 'https://graphixtechnoservices.com/wp-content/uploads/2017/11/AAEAAQAAAAAAAAbQAAAAJDEzOTI5Y2JiLWVjODItNDQ0NC05MmM3LTY3ZmE0NmUzZTM1ZQ.jpg',
  civil: 'https://graphixtechnoservices.com/wp-content/uploads/2017/11/Civil-CAD-Courses.jpg',
  electrical: 'https://graphixtechnoservices.com/wp-content/uploads/2017/11/electrical.jpeg',
  placementsHero: 'https://graphixtechnoservices.com/wp-content/uploads/2017/11/placements.jpg',
  events: 'https://graphixtechnoservices.com/wp-content/uploads/2017/10/events.jpg',
  businessCareer: 'https://graphixtechnoservices.com/wp-content/uploads/2018/12/business-career-confidence-776615-1024x683.jpg',
  placementCollage: [
    'https://graphixtechnoservices.com/wp-content/uploads/2018/12/International-Picnic-Day-11.png',
    'https://graphixtechnoservices.com/wp-content/uploads/2018/12/International-Picnic-Day-9.png',
    'https://graphixtechnoservices.com/wp-content/uploads/2018/12/International-Picnic-Day-2.png',
    'https://graphixtechnoservices.com/wp-content/uploads/2018/12/International-Picnic-Day-10.png',
    'https://graphixtechnoservices.com/wp-content/uploads/2018/12/WhatsApp-Image-2018-12-17-at-5.08.05-PM.jpeg',
    'https://graphixtechnoservices.com/wp-content/uploads/2018/12/WhatsApp-Image-2018-12-20-at-3.34.01-PM.jpeg',
    'https://graphixtechnoservices.com/wp-content/uploads/2018/12/WhatsApp-Image-2018-12-18-at-12.14.45-PM.jpeg',
    'https://graphixtechnoservices.com/wp-content/uploads/2018/12/WhatsApp-Image-2019-01-05-at-10.59.16-AM.jpeg',
  ],
  testimonials: [
    'https://graphixtechnoservices.com/wp-content/uploads/2018/12/WhatsApp-Image-2019-01-05-at-10.59.16-AM.jpeg',
    'https://graphixtechnoservices.com/wp-content/uploads/2018/12/WhatsApp-Image-2019-01-05-at-11.45.32-PM.jpeg',
    'https://graphixtechnoservices.com/wp-content/uploads/2018/12/WhatsApp-Image-2019-01-11-at-7.20.01-PM.jpeg',
  ],
  whatsappFloat: 'https://graphixtechnoservices.com/wp-content/uploads/2022/03/WhatsApp-Image-2022-03-31-at-2.59.40-PM.jpeg',
  thumbCert: 'https://graphixtechnoservices.com/wp-content/uploads/elementor/thumbs/WhatsApp-Image-2021-04-29-at-12.59.10-PM-phsjk2njv8nw0fxey0f42be2zh64yh572e239sn2w4.jpeg'
};

const TOP_FEATURES = [
  'Central Government ISO Certification.',
  'Free revision batches allowed.',
  'Advance course material.',
  'Industrial training Central Government CAD/CAM/CAE Training Institute.',
  'A Unique Facility – Life Time Student Membership.',
  'Weekly New Batches For New Joiner.',
  'Industrial Training With Live Projects.',
  'Placements & Campus Drives'
];

const COURSES_MECH = ['AutoCad', 'Catia', 'Solidworks', 'Autodesk Inventor', 'AutoCAD Plant 3D', 'Uni-graphics (UG-NX)', 'Creo', 'Revit MEP'];
const COURSES_CIVIL = ['AutoCad', 'Revit Architecture', 'Revit Structure', 'AutoCad Advance Steel', 'AutoCAD Plant 3D', 'Navis Work', '3Ds Max Studio', 'Revit MEP'];
const COURSES_ELEC = ['AutoCad', 'Autodesk Inventor', 'AutoCAD Plant 3D', 'Revit MEP'];

const JOB_ORIENTED = [
  { title: 'BIM Design Course', desc: 'Building Information Modelling – 100% Placement' },
  { title: 'HVAC Design Course', desc: 'Heating, Ventilation & AC Systems' },
  { title: 'Architectural Design Course', desc: 'Concept to Execution' },
  { title: 'Structural Design Course', desc: 'Analysis & Detailing' },
  { title: 'Piping Design Course', desc: 'Plant & Piping Layouts' },
  { title: 'Interior Design Course', desc: 'Space & Aesthetics' },
  { title: 'Electrical Design Course', desc: 'Power Systems & Distribution' },
];

const IT_COURSES = ['Core Java Course', 'Java Full Stack Developer', 'J2EE (Advance Java)', 'Data Science – Machine Learning & AI', 'Communication Training'];

const SERVICES = [
  { title: 'Product Design And Development', icon: <DesignServices /> },
  { title: 'Reverse Engineering And Remastering', icon: <Engineering /> },
  { title: '2D & 3D Data Conversion', icon: <Draw /> },
  { title: 'Jigs And Fixtures Design', icon: <Build /> },
  { title: 'CAE & CFD', icon: <Memory /> },
  { title: 'SPM Design & Concept', icon: <Factory /> },
  { title: 'Sheetmetal Design Services', icon: <Architecture /> },
  { title: '3D CAD Solid Modelling', icon: <HomeWork /> },
];

const INDUSTRY_NEEDS = [
  { title: 'Technical Knowledge', desc: 'Machines, tools, Engine, Operation & Maintenance.' },
  { title: 'Drawing Standards', desc: 'Projection Method, Dimensioning, Sheet Sizes, BOM, Ballooning, Title Block.' },
  { title: 'Design Parameters', desc: 'Cost, Delivery, Quantity, Quality, Energy, Reliability, Size, Weight.' },
  { title: 'Manufacturing Process', desc: 'Casting, Coating, Machining, Forming, Joining, Moulding, Welding.' },
  { title: 'Material Properties', desc: 'Elastic/Plastic deformation, Yield stress, Tensile strength, Ductility.' },
  { title: 'GD & T Knowledge', desc: 'Geometric Dimensioning & Tolerancing Application.' },
];

export const LandingPage = ({ onOpenLogin, onOpenEnquiry }) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [courseAnchor, setCourseAnchor] = useState(null);
  const [serviceAnchor, setServiceAnchor] = useState(null);

  // Pre-warm the sleeping Render backend while the visitor reads the landing
  // page, so the login that follows is already warm.
  useEffect(() => {
    warmBackend();
  }, []);

  const scrollTo = (id) => {
    setMobileOpen(false);
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const handleOpenAi = (q) => window.dispatchEvent(new CustomEvent('open-rag-assistant', { detail: q ? { query: q } : {} }));

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default', color: 'text.primary', overflowX: 'hidden' }}>
      {/* Top Bar */}
      <Box sx={{ bgcolor: '#0F172A', color: 'rgba(255,255,255,0.85)', py: 0.7, borderBottom: '1px solid rgba(255,255,255,0.08)', fontSize: '0.82rem', display: { xs: 'none', md: 'block' } }}>
        <Container maxWidth="xl" sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2 }}>
          <Stack direction="row" spacing={2.5} alignItems="center">
            <Stack direction="row" spacing={0.7} alignItems="center"><Phone sx={{ fontSize: 16, color: '#34D399' }} /><MuiLink href="tel:+919970720023" underline="hover" sx={{ color: 'inherit', fontWeight: 600 }}>+91 9970720023</MuiLink></Stack>
            <Stack direction="row" spacing={0.7} alignItems="center"><Email sx={{ fontSize: 16, color: '#818CF8' }} /><MuiLink href="mailto:info@graphixtech.org" underline="hover" sx={{ color: 'inherit' }}>info@graphixtech.org</MuiLink></Stack>
            <Chip size="small" label="Central Government CAD/CAM/CAE Training Institute" sx={{ bgcolor: 'rgba(99,102,241,0.15)', color: '#A5B4FC', border: '1px solid rgba(129,140,248,0.2)', height: 22, fontSize: '0.7rem', fontWeight: 600 }} />
          </Stack>
          <Stack direction="row" spacing={1.2} alignItems="center">
            <Typography variant="caption" sx={{ opacity: 0.7, mr: 1 }}>Follow us:</Typography>
            <IconButton size="small" href="https://www.facebook.com/graphix.technologies/" target="_blank" sx={{ color: 'rgba(255,255,255,0.7)', '&:hover': { color: '#fff' } }}><Facebook fontSize="small" /></IconButton>
            <IconButton size="small" href="https://instagram.com/graphix.technologies" target="_blank" sx={{ color: 'rgba(255,255,255,0.7)', '&:hover': { color: '#fff' } }}><Instagram fontSize="small" /></IconButton>
            <IconButton size="small" href="https://www.linkedin.com/company/infinite-graphix-technologies-pvt-ltd/" target="_blank" sx={{ color: 'rgba(255,255,255,0.7)', '&:hover': { color: '#fff' } }}><LinkedIn fontSize="small" /></IconButton>
          </Stack>
        </Container>
      </Box>

      {/* Sticky Nav */}
      <AppBar position="sticky" elevation={0} sx={{ bgcolor: 'background.paper', borderBottom: '1px solid', borderColor: 'divider', color: 'text.primary', backdropFilter: 'blur(10px)' }}>
        <Container maxWidth="xl">
          <Toolbar disableGutters sx={{ gap: 2, py: 0.5 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexShrink: 0, cursor: 'pointer' }} onClick={() => scrollTo('hero')}>
              <Box component="img" src={IMG.logo} alt="Graphix Technologies" loading="lazy" sx={{ width: 44, height: 44, borderRadius: 2, objectFit: 'cover', border: '1px solid', borderColor: 'divider' }} />
              <Box>
                <Typography variant="subtitle1" sx={{ fontWeight: 800, lineHeight: 1, letterSpacing: 0.3 }}>Graphix Technologies</Typography>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, letterSpacing: 0.5 }}>Central Govt. Certified • CRM-Powered</Typography>
              </Box>
            </Box>

            <Box sx={{ flexGrow: 1, display: { xs: 'none', lg: 'flex' }, justifyContent: 'center', gap: 0.5 }}>
              <Button onClick={() => scrollTo('about')} sx={{ color: 'text.primary', fontWeight: 600, textTransform: 'none' }}>About Us</Button>
              <Button onMouseEnter={(e) => setCourseAnchor(e.currentTarget)} onClick={(e) => setCourseAnchor(e.currentTarget)} sx={{ color: 'text.primary', fontWeight: 600, textTransform: 'none' }}>Courses ▾</Button>
              <Button onMouseEnter={(e) => setServiceAnchor(e.currentTarget)} onClick={(e) => setServiceAnchor(e.currentTarget)} sx={{ color: 'text.primary', fontWeight: 600, textTransform: 'none' }}>Services ▾</Button>
              <Button onClick={() => scrollTo('placements')} sx={{ color: 'text.primary', fontWeight: 600, textTransform: 'none' }}>Placements</Button>
              <Button onClick={() => scrollTo('events')} sx={{ color: 'text.primary', fontWeight: 600, textTransform: 'none' }}>Events</Button>
              <Button onClick={() => scrollTo('branches')} sx={{ color: 'text.primary', fontWeight: 600, textTransform: 'none' }}>Contact</Button>
            </Box>

            {/* Mega menus */}
            <Menu anchorEl={courseAnchor} open={Boolean(courseAnchor)} onClose={() => setCourseAnchor(null)} MenuListProps={{ onMouseLeave: () => setCourseAnchor(null) }} PaperProps={{ sx: { p: 2, minWidth: 720, borderRadius: 3 } }}>
              <Grid container spacing={2}>
                <Grid item xs={4}><Typography variant="subtitle2" sx={{ fontWeight: 800, mb: 1, color: 'primary.main' }}>Mechanical CAD</Typography><Stack spacing={0.5}>{COURSES_MECH.map(c => <MuiLink key={c} href="#" underline="hover" sx={{ fontSize: '0.85rem' }}>{c}</MuiLink>)}</Stack></Grid>
                <Grid item xs={4}><Typography variant="subtitle2" sx={{ fontWeight: 800, mb: 1, color: 'primary.main' }}>Civil CAD</Typography><Stack spacing={0.5}>{COURSES_CIVIL.map(c => <MuiLink key={c} href="#" underline="hover" sx={{ fontSize: '0.85rem' }}>{c}</MuiLink>)}</Stack></Grid>
                <Grid item xs={4}><Typography variant="subtitle2" sx={{ fontWeight: 800, mb: 1, color: 'primary.main' }}>Job Oriented (100% Placement)</Typography><Stack spacing={0.5}>{JOB_ORIENTED.slice(0, 6).map(j => <MuiLink key={j.title} href="#" underline="hover" sx={{ fontSize: '0.85rem' }}>{j.title}</MuiLink>)}</Stack></Grid>
              </Grid>
            </Menu>
            <Menu anchorEl={serviceAnchor} open={Boolean(serviceAnchor)} onClose={() => setServiceAnchor(null)} MenuListProps={{ onMouseLeave: () => setServiceAnchor(null) }} PaperProps={{ sx: { p: 2, minWidth: 520, borderRadius: 3 } }}>
              <Grid container spacing={1}>
                {SERVICES.map(s => (
                  <Grid item xs={6} key={s.title}><Stack direction="row" spacing={1} alignItems="center" sx={{ p: 1, borderRadius: 2, '&:hover': { bgcolor: 'action.hover' } }}><Box sx={{ color: 'primary.main' }}>{s.icon}</Box><Typography variant="body2" sx={{ fontWeight: 600 }}>{s.title}</Typography></Stack></Grid>
                ))}
              </Grid>
            </Menu>

            <Stack direction="row" spacing={1} alignItems="center" sx={{ flexShrink: 0 }}>
              <Button variant="outlined" onClick={handleOpenAi} startIcon={<SmartToy />} sx={{ display: { xs: 'none', md: 'inline-flex' }, borderRadius: 2.5, textTransform: 'none', fontWeight: 700, borderColor: 'rgba(16,185,129,0.4)', color: '#059669' }}>Ask AI</Button>
              <Button variant="outlined" onClick={onOpenEnquiry} sx={{ display: { xs: 'none', sm: 'inline-flex' }, borderRadius: 2.5, textTransform: 'none', fontWeight: 700 }}>Enquiry</Button>
              <Button variant="contained" onClick={onOpenLogin} sx={{ borderRadius: 2.5, textTransform: 'none', fontWeight: 800, background: 'linear-gradient(135deg, #6366F1 0%, #10B981 100%)', boxShadow: '0 6px 18px rgba(99,102,241,0.25)' }}>Login / CRM</Button>
              <IconButton sx={{ display: { lg: 'none' } }} onClick={() => setMobileOpen(true)}><MenuIcon /></IconButton>
            </Stack>
          </Toolbar>
        </Container>
      </AppBar>

      <Drawer anchor="right" open={mobileOpen} onClose={() => setMobileOpen(false)} PaperProps={{ sx: { width: 320 } }}>
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><Typography variant="h6" fontWeight={800}>Menu</Typography><IconButton onClick={() => setMobileOpen(false)}><Close /></IconButton></Box>
        <Divider />
        <List>
          {[
            { label: 'About', id: 'about' },
            { label: 'CAD Courses', id: 'courses' },
            { label: 'Placements', id: 'placements' },
            { label: 'Services', id: 'services' },
            { label: 'Events', id: 'events' },
            { label: 'Branches & Contact', id: 'branches' },
          ].map(i => <ListItem key={i.id} button onClick={() => scrollTo(i.id)}><ListItemText primary={i.label} /></ListItem>)}
        </List>
        <Box sx={{ p: 2 }}>
          <Button fullWidth variant="contained" onClick={() => { setMobileOpen(false); onOpenLogin(); }} sx={{ mb: 1, background: 'linear-gradient(135deg, #6366F1 0%, #10B981 100%)' }}>Go to CRM Login</Button>
          <Button fullWidth variant="outlined" onClick={() => { setMobileOpen(false); onOpenEnquiry(); }}>Admission Enquiry</Button>
        </Box>
      </Drawer>

      {/* HERO */}
      <Box id="hero" sx={{ position: 'relative', overflow: 'hidden', background: 'radial-gradient(1200px 600px at 10% -10%, rgba(99,102,241,0.12) 0%, transparent 60%), radial-gradient(1000px 500px at 90% 0%, rgba(16,185,129,0.12) 0%, transparent 60%), linear-gradient(180deg, background.paper 0%, background.default 100%)', py: { xs: 4, md: 7 } }}>
        <Container maxWidth="xl">
          <Grid container spacing={4} alignItems="center">
            <Grid item xs={12} md={6.5}>
              <Stack spacing={2.2}>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                  <Chip icon={<Verified sx={{ fontSize: 16 }} />} label="BECIL • Govt. of India Enterprise • ISO Certified" size="small" sx={{ bgcolor: 'rgba(99,102,241,0.1)', color: 'primary.main', fontWeight: 700, border: '1px solid rgba(99,102,241,0.2)' }} />
                  <Chip label="Admissions Open 2026 – Weekly New Batches" size="small" color="success" variant="outlined" sx={{ fontWeight: 700 }} />
                </Stack>
                <Typography variant="h2" sx={{ fontWeight: 900, lineHeight: 0.95, fontSize: { xs: '2rem', sm: '2.6rem', lg: '3.2rem' }, letterSpacing: -1 }}>
                  CAD Courses in Pune <Box component="span" sx={{ background: 'linear-gradient(135deg, #6366F1 0%, #10B981 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>with 100% Placement Assistance</Box>
                </Typography>
                <Typography variant="body1" sx={{ color: 'text.secondary', fontSize: '1.05rem', maxWidth: 640 }}>
                  Central Government CAD/CAM/CAE Training Institute • Industry-aligned curriculum, lifetime membership, free revision batches & live project training — now managed on our unified CRM & ERP platform.
                </Typography>
                <Paper elevation={0} sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', borderRadius: 3, bgcolor: 'background.paper' }}>
                  <Grid container spacing={1}>
                    {TOP_FEATURES.map(f => (
                      <Grid item xs={12} sm={6} key={f}>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <CheckCircle sx={{ color: 'success.main', fontSize: 18, flexShrink: 0 }} />
                          <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.88rem' }}>{f}</Typography>
                        </Stack>
                      </Grid>
                    ))}
                  </Grid>
                </Paper>
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ pt: 1 }}>
                  <Button size="large" variant="contained" endIcon={<ArrowForward />} onClick={onOpenEnquiry} sx={{ borderRadius: 3, px: 3, py: 1.4, fontWeight: 800, background: 'linear-gradient(135deg, #6366F1 0%, #0EA5E9 100%)' }}>Book Free Demo & Counseling</Button>
                  <Button size="large" variant="outlined" startIcon={<PlayCircle />} onClick={() => handleOpenAi('Tell me about CAD courses, fees and placements')} sx={{ borderRadius: 3, px: 3, py: 1.4, fontWeight: 700, borderColor: 'primary.main' }}>Chat with AI Counselor</Button>
                </Stack>
                <Stack direction="row" spacing={2.5} divider={<Divider orientation="vertical" flexItem />} sx={{ pt: 1 }}>
                  <Box><Typography variant="h5" fontWeight={900} color="primary.main">80+ MNCs</Typography><Typography variant="caption" color="text.secondary" fontWeight={600}>Hiring Partners</Typography></Box>
                  <Box><Typography variant="h5" fontWeight={900} color="primary.main">200+ Companies</Typography><Typography variant="caption" color="text.secondary" fontWeight={600}>Placement Network</Typography></Box>
                  <Box><Typography variant="h5" fontWeight={900} color="success.main">100%</Typography><Typography variant="caption" color="text.secondary" fontWeight={600}>Placement Assistance</Typography></Box>
                </Stack>
              </Stack>
            </Grid>
            <Grid item xs={12} md={5.5}>
              <Box sx={{ position: 'relative' }}>
                <Card sx={{ borderRadius: 4, overflow: 'hidden', border: '1px solid', borderColor: 'divider', boxShadow: '0 20px 40px rgba(0,0,0,0.12)' }}>
                  <CardMedia component="img" image={IMG.cloud} alt="CAD CAM CAE Training - Cloud & Design Lab" loading="lazy" sx={{ height: { xs: 240, md: 360 }, objectFit: 'cover' }} />
                  <CardContent sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', bgcolor: 'primary.main', color: '#fff', py: 1.2 }}>
                    <Stack direction="row" spacing={1.2} alignItems="center"><Cloud sx={{ color: '#fff' }} /><Typography variant="subtitle2" fontWeight={800}>Cloud Computing & CAD Labs</Typography></Stack>
                    <Chip label="Live Projects" size="small" sx={{ bgcolor: '#fff', color: 'primary.main', fontWeight: 800 }} />
                  </CardContent>
                </Card>
                {/* Floating mini card */}
                <Paper sx={{ position: 'absolute', bottom: -18, left: { xs: 12, md: -18 }, right: { xs: 12, md: 'auto' }, p: 1.5, borderRadius: 3, display: 'flex', gap: 1.5, alignItems: 'center', border: '1px solid', borderColor: 'divider', boxShadow: '0 12px 24px rgba(0,0,0,0.12)', maxWidth: 360 }}>
                  <Avatar src={IMG.thumbCert} sx={{ width: 48, height: 48 }} />
                  <Box>
                    <Typography variant="body2" fontWeight={800}>Govt. ISO Certification Valid in 82+ Countries</Typography>
                    <Typography variant="caption" color="text.secondary">Preferred in Design Industry • Private & Govt. Jobs</Typography>
                  </Box>
                </Paper>
                <Box sx={{ position: 'absolute', top: -14, right: -10, display: { xs: 'none', md: 'flex' }, alignItems: 'center', gap: 1, bgcolor: 'success.main', color: '#fff', px: 1.6, py: 0.8, borderRadius: 10, boxShadow: '0 8px 18px rgba(16,185,129,0.35)', fontWeight: 800, fontSize: '0.8rem' }}>
                  <Star sx={{ fontSize: 16 }} /> 4.8/5 Student Rating
                </Box>
              </Box>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* Stats / Trust */}
      <Container maxWidth="xl" sx={{ py: 2 }}>
        <Paper elevation={0} sx={{ p: { xs: 2, md: 2.5 }, borderRadius: 3, border: '1px solid', borderColor: 'divider', display: 'flex', gap: 3, flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', bgcolor: 'background.paper' }}>
          {[
            { icon: <WorkspacePremium color="primary" />, label: 'Govt. ISO Certified Courses' },
            { icon: <AutoGraph color="success" />, label: 'Life Time Student Membership' },
            { icon: <Groups color="info" />, label: 'Industrial Faculties 1.5+ Yrs Exp.' },
            { icon: <SupportAgent color="warning" />, label: 'Weekly New Batches' },
          ].map(s => (
            <Stack key={s.label} direction="row" spacing={1.2} alignItems="center"><Box sx={{ width: 36, height: 36, borderRadius: 2, bgcolor: 'action.hover', display: 'grid', placeItems: 'center' }}>{s.icon}</Box><Typography variant="body2" fontWeight={700}>{s.label}</Typography></Stack>
          ))}
          <Chip label="CRM-managed batches, attendance, fees & placements" size="small" color="primary" variant="outlined" sx={{ fontWeight: 700 }} />
        </Paper>
      </Container>

      {/* Placements */}
      <Box id="placements" sx={{ py: { xs: 4, md: 6 }, bgcolor: 'background.paper', borderTop: '1px solid', borderBottom: '1px solid', borderColor: 'divider' }}>
        <Container maxWidth="xl">
          <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ md: 'center' }} spacing={1} sx={{ mb: 3 }}>
            <Box>
              <Typography variant="overline" sx={{ color: 'primary.main', fontWeight: 800, letterSpacing: 1.2 }}>Our Students Placements</Typography>
              <Typography variant="h4" fontWeight={900}>Placed in Leading Design & Manufacturing MNCs</Typography>
              <Typography variant="body2" color="text.secondary">80+ MNC Companies • 200+ Hiring Partners • Campus Drives at Institute</Typography>
            </Box>
            <Button variant="outlined" endIcon={<ArrowForward />} onClick={onOpenEnquiry} sx={{ borderRadius: 2.5, textTransform: 'none', fontWeight: 700, alignSelf: { xs: 'flex-start', md: 'center' } }}>View All Placements</Button>
          </Stack>
          <Grid container spacing={1.5}>
            {IMG.placementCollage.map((src, i) => (
              <Grid key={src + i} item xs={6} sm={3} md={3} lg={1.5}>
                <Card sx={{ borderRadius: 3, overflow: 'hidden', border: '1px solid', borderColor: 'divider', height: 140 }}>
                  <CardMedia component="img" image={src} alt={`Placement ${i + 1}`} loading="lazy" sx={{ height: '100%', objectFit: 'cover' }} />
                </Card>
              </Grid>
            ))}
          </Grid>
          <Box sx={{ mt: 2, textAlign: 'center' }}>
            <Typography variant="caption" color="text.secondary">Images are actual placement drives & student achievement moments from Graphix campuses (imported for demo, © Graphix Technologies).</Typography>
          </Box>
        </Container>
      </Box>

      {/* CAD Courses */}
      <Box id="courses" sx={{ py: { xs: 4, md: 6 } }}>
        <Container maxWidth="xl">
          <Box sx={{ textAlign: 'center', mb: 4 }}>
            <Chip label="CAD Courses" size="small" color="primary" sx={{ fontWeight: 800, mb: 1 }} />
            <Typography variant="h4" fontWeight={900}>Mechanical • Civil • Electrical</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 720, mx: 'auto', mt: 1 }}>Industry-aligned curricula covering design standards, GD&T, BIM and live projects. All batches tracked via CRM for attendance, assignments & performance.</Typography>
          </Box>
          <Grid container spacing={2.5}>
            {[
              { title: 'Mechanical CAD Courses', img: IMG.mechanical, courses: COURSES_MECH, icon: <Engineering sx={{ color: 'primary.main' }} /> },
              { title: 'Civil CAD Courses', img: IMG.civil, courses: COURSES_CIVIL, icon: <Architecture sx={{ color: 'primary.main' }} /> },
              { title: 'Electrical CAD Courses', img: IMG.electrical, courses: COURSES_ELEC, icon: <ElectricalServices sx={{ color: 'primary.main' }} /> },
            ].map(card => (
              <Grid key={card.title} item xs={12} md={4}>
                <Card sx={{ height: '100%', borderRadius: 4, overflow: 'hidden', border: '1px solid', borderColor: 'divider', display: 'flex', flexDirection: 'column' }}>
                  <Box sx={{ position: 'relative' }}>
                    <CardMedia component="img" image={card.img} alt={card.title} loading="lazy" sx={{ height: 190, objectFit: 'cover' }} />
                    <Chip icon={card.icon} label={card.title} sx={{ position: 'absolute', bottom: -14, left: 16, bgcolor: 'background.paper', fontWeight: 800, border: '1px solid', borderColor: 'divider', boxShadow: 2 }} />
                  </Box>
                  <CardContent sx={{ pt: 3.5, flexGrow: 1 }}>
                    <Grid container spacing={1}>
                      {card.courses.map(c => (
                        <Grid key={c} item xs={6}>
                          <Stack direction="row" spacing={0.8} alignItems="center">
                            <CheckCircle sx={{ fontSize: 14, color: 'success.main', flexShrink: 0 }} />
                            <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.88rem' }}>{c}</Typography>
                          </Stack>
                        </Grid>
                      ))}
                    </Grid>
                  </CardContent>
                  <Box sx={{ p: 2, pt: 0 }}>
                    <Button fullWidth variant="contained" onClick={onOpenEnquiry} sx={{ borderRadius: 2.5, textTransform: 'none', fontWeight: 700 }}>Enquire for {card.title.split(' ')[0]} Batch</Button>
                  </Box>
                </Card>
              </Grid>
            ))}
          </Grid>

          {/* Placements mini + Certification */}
          <Grid container spacing={2.5} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <Card sx={{ borderRadius: 3, border: '1px solid', borderColor: 'divider', height: '100%', display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, overflow: 'hidden' }}>
                <CardMedia component="img" image={IMG.placementsHero} alt="Placements" loading="lazy" sx={{ width: { xs: '100%', sm: 220 }, height: { xs: 180, sm: 'auto' }, objectFit: 'cover' }} />
                <CardContent>
                  <Typography variant="h6" fontWeight={800}>Placements</Typography>
                  <Stack spacing={0.7} sx={{ mt: 1 }}>
                    {['80+ MNC Companies', '100% Placement Assistance', 'More Than 200+ Companies', 'Campus Drive At Institute', 'Campus Placements'].map(t => (
                      <Stack key={t} direction="row" spacing={1} alignItems="center"><CheckCircle sx={{ fontSize: 16, color: 'primary.main' }} /><Typography variant="body2" fontWeight={600}>{t}</Typography></Stack>
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card sx={{ borderRadius: 3, border: '1px solid', borderColor: 'divider', height: '100%', p: 0, overflow: 'hidden' }}>
                <Box sx={{ display: 'flex', gap: 2, p: 2.5, alignItems: 'center' }}>
                  <Box sx={{ width: 56, height: 56, borderRadius: 2, bgcolor: 'primary.main', display: 'grid', placeItems: 'center', color: '#fff' }}><Verified /></Box>
                  <Box><Typography variant="h6" fontWeight={800}>Certification</Typography><Typography variant="caption" color="text.secondary" fontWeight={600}>Central Government ISO Certified • BECIL Enterprise</Typography></Box>
                </Box>
                <Divider />
                <Box sx={{ p: 2.5 }}>
                  <Stack spacing={1}>
                    {[
                      'Cad Courses With Central Government ISO Certification.',
                      'BECIL – A Government Of India Enterprise.',
                      'Valid For Private And Government Jobs In 82+ Countries.',
                      'Applicable As Per State Wise Government Placements.',
                      'Most Preferred In Design Industry.'
                    ].map(t => <Stack key={t} direction="row" spacing={1}><CheckCircle sx={{ fontSize: 16, color: 'success.main', mt: 0.3 }} /><Typography variant="body2">{t}</Typography></Stack>)}
                  </Stack>
                </Box>
              </Card>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* Job Oriented + IT */}
      <Box sx={{ py: { xs: 3, md: 5 }, bgcolor: 'background.paper', borderTop: '1px solid', borderBottom: '1px solid', borderColor: 'divider' }}>
        <Container maxWidth="xl">
          <Grid container spacing={2.5}>
            <Grid item xs={12} md={7}>
              <Typography variant="h5" fontWeight={900} sx={{ mb: 1 }}>100% Placement Based Job Oriented Courses</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>BIM, HVAC, Architectural, Structural, Piping, Interior & Electrical Design – with institute CRM tracking leads to placements.</Typography>
              <Grid container spacing={1.5}>
                {JOB_ORIENTED.map(j => (
                  <Grid key={j.title} item xs={12} sm={6}>
                    <Paper elevation={0} sx={{ p: 1.8, borderRadius: 3, border: '1px solid', borderColor: 'divider', display: 'flex', gap: 1.2, alignItems: 'center', '&:hover': { borderColor: 'primary.main' } }}>
                      <Box sx={{ width: 40, height: 40, borderRadius: 2, bgcolor: 'rgba(99,102,241,0.1)', display: 'grid', placeItems: 'center', color: 'primary.main' }}><DesignServices fontSize="small" /></Box>
                      <Box><Typography variant="subtitle2" fontWeight={800}>{j.title}</Typography><Typography variant="caption" color="text.secondary">{j.desc}</Typography></Box>
                    </Paper>
                  </Grid>
                ))}
              </Grid>
            </Grid>
            <Grid item xs={12} md={5}>
              <Card sx={{ borderRadius: 3, border: '1px solid', borderColor: 'divider', overflow: 'hidden' }}>
                <CardMedia component="img" image={IMG.cloud} alt="Cloud & IT" loading="lazy" sx={{ height: 180, objectFit: 'cover' }} />
                <CardContent>
                  <Typography variant="h6" fontWeight={800}>IT & Cloud Computing</Typography>
                  <Stack spacing={1} sx={{ mt: 1.5 }}>
                    {IT_COURSES.map(c => <Stack key={c} direction="row" spacing={1} alignItems="center"><Code sx={{ fontSize: 16, color: 'primary.main' }} /><Typography variant="body2" fontWeight={600}>{c}</Typography></Stack>)}
                  </Stack>
                  <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
                    <Chip icon={<Cloud />} label="Salesforce" size="small" color="primary" variant="outlined" />
                    <Chip icon={<Storage />} label="AWS Certification" size="small" color="success" variant="outlined" />
                  </Stack>
                  <Button fullWidth variant="contained" sx={{ mt: 2, borderRadius: 2.5, textTransform: 'none' }} onClick={() => handleOpenAi('What IT courses do you offer?')}>Ask AI about IT Courses</Button>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Additional inline cloud-computing promo */}
          <Paper elevation={0} sx={{ mt: 3, p: 2, borderRadius: 3, border: '1px solid', borderColor: 'divider', display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap', bgcolor: 'rgba(99,102,241,0.04)' }}>
            <Box component="img" src={IMG.cloud} alt="Cloud" loading="lazy" sx={{ width: 110, height: 70, borderRadius: 2, objectFit: 'cover' }} />
            <Box sx={{ flex: 1, minWidth: 220 }}><Typography variant="subtitle2" fontWeight={800}>Cloud Computing Courses • Salesforce & AWS</Typography><Typography variant="caption" color="text.secondary">Upskill for cloud roles with hands-on labs & certification guidance.</Typography></Box>
            <Button variant="outlined" endIcon={<ArrowForward />} onClick={onOpenEnquiry} sx={{ borderRadius: 2.5, textTransform: 'none', fontWeight: 700 }}>Enquire Now</Button>
          </Paper>
        </Container>
      </Box>

      {/* Services */}
      <Box id="services" sx={{ py: { xs: 4, md: 6 } }}>
        <Container maxWidth="xl">
          <Box sx={{ textAlign: 'center', mb: 3 }}>
            <Typography variant="overline" sx={{ color: 'primary.main', fontWeight: 800 }}>Services</Typography>
            <Typography variant="h4" fontWeight={900}>Design & Engineering Services</Typography>
            <Typography variant="body2" color="text.secondary">Product Design, Reverse Engineering, CAE/CFD & Manufacturing Support – delivered by industrial experts.</Typography>
          </Box>
          <Grid container spacing={1.6}>
            {SERVICES.map(s => (
              <Grid key={s.title} item xs={12} sm={6} md={3}>
                <Card sx={{ height: '100%', borderRadius: 3, border: '1px solid', borderColor: 'divider', p: 2, display: 'flex', flexDirection: 'column', gap: 1.2, '&:hover': { borderColor: 'primary.main', boxShadow: '0 8px 18px rgba(0,0,0,0.08)' } }}>
                  <Box sx={{ width: 44, height: 44, borderRadius: 2, bgcolor: 'primary.main', color: '#fff', display: 'grid', placeItems: 'center' }}>{s.icon}</Box>
                  <Typography variant="subtitle2" fontWeight={800}>{s.title}</Typography>
                  <Typography variant="caption" color="text.secondary">Export-grade deliverables, optimized via CRM project tracking.</Typography>
                </Card>
              </Grid>
            ))}
          </Grid>
          <Stack direction="row" spacing={1} justifyContent="center" sx={{ mt: 2, flexWrap: 'wrap' }}>
            <Chip label="2D & 3D Data Conversion" size="small" />
            <Chip label="Manufacturing Drawing & Drafting" size="small" />
            <Chip label="SPM Design & Concept" size="small" />
            <Chip label="Jigs & Fixtures" size="small" />
          </Stack>
        </Container>
      </Box>

      {/* Industry Needs */}
      <Box sx={{ py: { xs: 4, md: 6 }, bgcolor: 'background.paper', borderTop: '1px solid', borderBottom: '1px solid', borderColor: 'divider' }}>
        <Container maxWidth="xl">
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} md={5}>
              <Box component="img" src={IMG.businessCareer} alt="What industry requires from CAD engineer" loading="lazy" sx={{ width: '100%', borderRadius: 4, border: '1px solid', borderColor: 'divider', objectFit: 'cover', maxHeight: 380 }} />
            </Grid>
            <Grid item xs={12} md={7}>
              <Typography variant="overline" sx={{ color: 'primary.main', fontWeight: 800 }}>Industry Insights</Typography>
              <Typography variant="h4" fontWeight={900}>What Industry Require From CAD Engineer?</Typography>
              <Typography variant="caption" color="text.secondary" fontWeight={600}>Article by – Kishor More, State Coordinator & MD Graphix Technologies</Typography>
              <Grid container spacing={1.5} sx={{ mt: 1.5 }}>
                {INDUSTRY_NEEDS.map(n => (
                  <Grid key={n.title} item xs={12} sm={6}>
                    <Paper elevation={0} sx={{ p: 1.7, borderRadius: 3, border: '1px solid', borderColor: 'divider', height: '100%' }}>
                      <Typography variant="subtitle2" fontWeight={800} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}><FindInPage sx={{ fontSize: 18, color: 'primary.main' }} />{n.title}</Typography>
                      <Typography variant="caption" color="text.secondary">{n.desc}</Typography>
                    </Paper>
                  </Grid>
                ))}
              </Grid>
              <Button variant="outlined" sx={{ mt: 2, borderRadius: 2.5, textTransform: 'none' }} onClick={() => handleOpenAi('What does industry require from a CAD engineer?')}>Ask AI for full article</Button>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* Events & Team */}
      <Box id="events" sx={{ py: { xs: 4, md: 5 } }}>
        <Container maxWidth="xl">
          <Grid container spacing={2.5}>
            <Grid item xs={12} md={6}>
              <Card sx={{ borderRadius: 4, overflow: 'hidden', border: '1px solid', borderColor: 'divider', height: '100%' }}>
                <CardMedia component="img" image={IMG.events} alt="Events - Graphix Technologies" loading="lazy" sx={{ height: 220, objectFit: 'cover' }} />
                <CardContent>
                  <Typography variant="h6" fontWeight={800}>Events & Seminars</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>We successfully conduct Career Guidance Seminars in various colleges for educating & creating awareness regarding future goals. Live sessions synced via CRM events calendar.</Typography>
                  <Button size="small" endIcon={<ArrowForward />} sx={{ mt: 1, textTransform: 'none', fontWeight: 700 }}>View Events</Button>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card sx={{ borderRadius: 4, border: '1px solid', borderColor: 'divider', height: '100%', p: 2.5 }}>
                <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
                  <Avatar src={IMG.thumbCert} sx={{ width: 56, height: 56 }} />
                  <Box><Typography variant="h6" fontWeight={800}>Our Team</Typography><Typography variant="caption" color="text.secondary">Industrial Faculties • Minimum 1.5 Yrs Experience</Typography></Box>
                </Stack>
                <Stack spacing={1.2}>
                  <Paper elevation={0} sx={{ p: 1.6, borderRadius: 2, bgcolor: 'action.hover', border: '1px solid', borderColor: 'divider' }}><Typography variant="body2" fontWeight={700}>✓ Our Expertise With Industrial Knowledge.</Typography></Paper>
                  <Paper elevation={0} sx={{ p: 1.6, borderRadius: 2, bgcolor: 'action.hover', border: '1px solid', borderColor: 'divider' }}><Typography variant="body2" fontWeight={700}>✓ All Industrial Faculties With Minimum 1.5 Yrs Experience.</Typography></Paper>
                </Stack>
                <Box component="img" src={IMG.whatsappFloat} alt="Team - Graphix Technologies" loading="lazy" sx={{ width: '100%', mt: 2, borderRadius: 3, height: 'auto', maxHeight: 'none', objectFit: 'contain', display: 'block', border: '1px solid', borderColor: 'divider', bgcolor: 'background.default' }} />
              </Card>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* Testimonials */}
      <Box sx={{ py: { xs: 4, md: 6 }, bgcolor: '#0F172A', color: '#fff' }}>
        <Container maxWidth="xl">
          <Box sx={{ textAlign: 'center', mb: 3 }}>
            <Chip label="Testimonials" size="small" sx={{ bgcolor: 'rgba(99,102,241,0.2)', color: '#A5B4FC', fontWeight: 800, mb: 1 }} />
            <Typography variant="h4" fontWeight={900}>What Our Students Say</Typography>
          </Box>
          <Grid container spacing={2.5}>
            {[
              { name: 'Akash Nandure', role: 'CAD Engineer', quote: 'I always wanted to learn specific and need skills to become successful, but knew only a degree won’t help. Joining Graphix Technologies was the best decision – their training gave me required knowledge and skills.', img: IMG.testimonials[0] },
              { name: 'Anurag Devare', role: 'CAD Engineer', quote: 'Graphix Technologies is a great place for young students who want a job without spending a lot. I learnt a lot and they helped me get a stable job in a company of my choice.', img: IMG.testimonials[1] },
              { name: 'Rushikesh Tidke', role: 'CAD Engineer', quote: 'Completed course from Graphix and they provide excellent & quality training. Got placed in reputed company with complete placement support. Thank you Graphix Technologies.', img: IMG.testimonials[2] },
            ].map(t => (
              <Grid key={t.name} item xs={12} md={4}>
                <Card sx={{ height: '100%', borderRadius: 4, bgcolor: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', backdropFilter: 'blur(8px)', p: 2.5, color: '#fff' }}>
                  <Stack direction="row" spacing={1.2} sx={{ mb: 1.5 }}>
                    {[1, 2, 3, 4, 5].map(s => <Star key={s} sx={{ fontSize: 16, color: '#FBBF24' }} />)}
                  </Stack>
                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.85)', lineHeight: 1.6, mb: 2 }}>"{t.quote}"</Typography>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <Avatar src={t.img} sx={{ width: 44, height: 44, border: '2px solid rgba(255,255,255,0.2)' }} />
                    <Box><Typography variant="subtitle2" fontWeight={800}>{t.name}</Typography><Typography variant="caption" sx={{ color: '#A5B4FC' }}>{t.role}</Typography></Box>
                  </Stack>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Container>
      </Box>

      {/* Branches */}
      <Box id="branches" sx={{ py: { xs: 4, md: 6 }, bgcolor: 'background.paper' }}>
        <Container maxWidth="xl">
          <Box sx={{ textAlign: 'center', mb: 3 }}>
            <Typography variant="h4" fontWeight={900}>Our Branches</Typography>
            <Typography variant="body2" color="text.secondary">Visit any campus for counseling • All branches connected via CRM for unified admissions</Typography>
          </Box>
          <Grid container spacing={2}>
            {[
              { name: 'Shivaji Nagar Branch', addr: '2nd Floor, Kashinath Prasad Building, Above Bank Of Maharashtra, Near Modern Cafe, Shivajinagar, Pune, Maharashtra 411005.', phone: '+91 9970720023' },
              { name: 'PCMC Branch', addr: 'Mayur Trade Center Phase 1, Second Floor, P 202, Old Mumbai Pune Highway, Chinchwad, Pune, Maharashtra 411019.', phone: '+91 9970720023' },
              { name: 'Katraj Branch', addr: '2nd floor, Rishikesh Society, Plot 1, above New Poona bakery, near Pizza Hut, Katraj, Pune, Maharashtra 411046', phone: '+91 9970720023' },
            ].map(b => (
              <Grid key={b.name} item xs={12} md={4}>
                <Card sx={{ height: '100%', borderRadius: 3, border: '1px solid', borderColor: 'divider', p: 2.5 }}>
                  <Stack direction="row" spacing={1.2} alignItems="center" sx={{ mb: 1.2 }}><LocationOn color="primary" /><Typography variant="subtitle1" fontWeight={800}>{b.name}</Typography></Stack>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>{b.addr}</Typography>
                  <Stack direction="row" spacing={1} alignItems="center"><Phone sx={{ fontSize: 16, color: 'success.main' }} /><MuiLink href={`tel:${b.phone.replace(/\s/g, '')}`} underline="hover" sx={{ fontWeight: 700 }}>{b.phone}</MuiLink></Stack>
                  <Button size="small" variant="outlined" sx={{ mt: 1.5, borderRadius: 2, textTransform: 'none' }} startIcon={<LocationOn />}>Get Directions</Button>
                </Card>
              </Grid>
            ))}
          </Grid>

          {/* Contact CTA */}
          <Paper elevation={0} sx={{ mt: 3, p: { xs: 2.5, md: 3 }, borderRadius: 4, border: '1px solid', borderColor: 'divider', background: 'linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(16,185,129,0.08) 100%)', display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box>
              <Typography variant="h6" fontWeight={900}>Take First Step Towards Placement</Typography>
              <Typography variant="body2" color="text.secondary">Book a free site visit • Demo lecture • Career counseling – our CRM counselor will call back within 24 hrs.</Typography>
            </Box>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.2}>
              <Button variant="contained" size="large" onClick={onOpenEnquiry} startIcon={<Phone />} sx={{ borderRadius: 2.5, fontWeight: 800, background: 'linear-gradient(135deg, #6366F1 0%, #10B981 100%)' }}>Enquire Now – Free Demo</Button>
              <Button variant="outlined" size="large" href="tel:+919970720023" sx={{ borderRadius: 2.5, fontWeight: 700 }}>Call: 9970720023</Button>
            </Stack>
          </Paper>
        </Container>
      </Box>

      {/* Footer */}
      <Box component="footer" sx={{ bgcolor: '#0F172A', color: 'rgba(255,255,255,0.85)', pt: 5, borderTop: '1px solid rgba(255,255,255,0.08)' }}>
        <Container maxWidth="xl">
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Stack direction="row" spacing={1.2} alignItems="center" sx={{ mb: 1.5 }}>
                <Box component="img" src={IMG.logo} alt="Graphix" loading="lazy" sx={{ width: 40, height: 40, borderRadius: 2, objectFit: 'cover' }} />
                <Typography variant="h6" fontWeight={800} sx={{ color: '#fff' }}>Graphix Technologies</Typography>
              </Stack>
              <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)', mb: 1.5 }}>Central Government CAD/CAM/CAE Training Institute • Pune’s trusted CAD & Job-Oriented training with 100% placement assistance. CRM & ERP powered admissions, batch and fee management.</Typography>
              <Stack direction="row" spacing={1} alignItems="center"><Email sx={{ fontSize: 16, color: '#A5B4FC' }} /><MuiLink href="mailto:info@graphixtech.org" underline="hover" sx={{ color: '#A5B4FC' }}>info@graphixtech.org</MuiLink></Stack>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.5 }}><Phone sx={{ fontSize: 16, color: '#34D399' }} /><MuiLink href="tel:+919970720023" underline="hover" sx={{ color: '#34D399', fontWeight: 700 }}>+91 9970720023</MuiLink></Stack>
            </Grid>
            <Grid item xs={6} md={2}>
              <Typography variant="subtitle2" fontWeight={800} sx={{ color: '#fff', mb: 1.2 }}>Useful Links</Typography>
              <Stack spacing={0.7}>
                <MuiLink href="#" underline="hover" sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.9rem' }}>Home</MuiLink>
                <MuiLink href="#" underline="hover" sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.9rem' }} onClick={(e) => { e.preventDefault(); scrollTo('about'); }}>About Us</MuiLink>
                <MuiLink href="#" underline="hover" sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.9rem' }}>Career</MuiLink>
                <MuiLink href="#" underline="hover" sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.9rem' }} onClick={(e) => { e.preventDefault(); scrollTo('placements'); }}>Our Placements</MuiLink>
                <MuiLink href="#" underline="hover" sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.9rem' }} onClick={(e) => { e.preventDefault(); scrollTo('branches'); }}>Contact Us</MuiLink>
              </Stack>
            </Grid>
            <Grid item xs={6} md={3}>
              <Typography variant="subtitle2" fontWeight={800} sx={{ color: '#fff', mb: 1.2 }}>Courses</Typography>
              <Stack spacing={0.7}>
                <MuiLink href="#" underline="hover" sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.9rem' }}>Mechanical CAD (AutoCAD/CATIA/Solidworks/Creo/NX)</MuiLink>
                <MuiLink href="#" underline="hover" sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.9rem' }}>Civil CAD (Revit/3Ds Max/Navis)</MuiLink>
                <MuiLink href="#" underline="hover" sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.9rem' }}>Electrical CAD & Revit MEP</MuiLink>
                <MuiLink href="#" underline="hover" sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.9rem' }}>IT & Cloud (Salesforce/AWS/Java)</MuiLink>
              </Stack>
            </Grid>
            <Grid item xs={12} md={3}>
              <Typography variant="subtitle2" fontWeight={800} sx={{ color: '#fff', mb: 1.2 }}>Connect</Typography>
              <Stack direction="row" spacing={1} sx={{ mb: 1.5 }}>
                <IconButton href="https://www.facebook.com/graphix.technologies/" target="_blank" sx={{ bgcolor: 'rgba(255,255,255,0.08)', color: '#fff', '&:hover': { bgcolor: 'primary.main' } }}><Facebook fontSize="small" /></IconButton>
                <IconButton href="https://instagram.com/graphix.technologies" target="_blank" sx={{ bgcolor: 'rgba(255,255,255,0.08)', color: '#fff', '&:hover': { bgcolor: 'primary.main' } }}><Instagram fontSize="small" /></IconButton>
                <IconButton href="https://www.linkedin.com/company/infinite-graphix-technologies-pvt-ltd/" target="_blank" sx={{ bgcolor: 'rgba(255,255,255,0.08)', color: '#fff', '&:hover': { bgcolor: 'primary.main' } }}><LinkedIn fontSize="small" /></IconButton>
              </Stack>
              <Paper elevation={0} sx={{ p: 1.5, borderRadius: 2, bgcolor: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)' }}>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)', lineHeight: 1.4 }}>This landing is an <strong style={{ color: '#A5B4FC' }}>optimized clone</strong> of graphixtechnoservices.com adapted to the CRM theme. Assets hotlinked for demo; all original data © Graphix Technologies. Protected by CRM auth & RAG assistant.</Typography>
              </Paper>
            </Grid>
          </Grid>
          <Divider sx={{ my: 3, borderColor: 'rgba(255,255,255,0.08)' }} />
          <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems="center" spacing={1} sx={{ pb: 2 }}>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>Copyright © {new Date().getFullYear()} Graphix Technologies • Built on Institute CRM (React + MUI + PostgreSQL)</Typography>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Chip icon={<SmartToy sx={{ fontSize: 16 }} />} label="RAG AI Assistant" size="small" onClick={() => handleOpenAi()} sx={{ bgcolor: 'rgba(16,185,129,0.15)', color: '#34D399', fontWeight: 700, cursor: 'pointer', border: '1px solid rgba(16,185,129,0.3)' }} />
              <Button size="small" href="tel:09970720023" variant="contained" sx={{ borderRadius: 10, textTransform: 'none', fontWeight: 700, bgcolor: '#10B981' }} startIcon={<Phone sx={{ fontSize: 16 }} />}>Call Now</Button>
            </Stack>
          </Stack>
        </Container>
      </Box>

      {/* Floating Call Now */}
      <Box sx={{ position: 'fixed', bottom: 18, right: 18, display: { xs: 'none', md: 'flex' }, zIndex: 1200 }}>
        <Button href="tel:+919970720023" variant="contained" startIcon={<Phone />} sx={{ borderRadius: 10, px: 2.2, py: 1.2, fontWeight: 800, background: 'linear-gradient(135deg, #0EA5E9 0%, #6366F1 100%)', boxShadow: '0 8px 24px rgba(99,102,241,0.35)' }}>Call Now</Button>
      </Box>
    </Box>
  );
};

export default LandingPage;
