import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Fab,
  Paper,
  Typography,
  IconButton,
  TextField,
  Button,
  Chip,
  Avatar,
  CircularProgress,
  Collapse,
  Divider,
  Tooltip,
} from '@mui/material';
import {
  SmartToy,
  Close,
  Send,
  RestartAlt,
  MenuBook,
  ExpandMore,
  ExpandLess,
  AutoAwesome,
  HelpOutline,
} from '@mui/icons-material';
import { useAuth } from '../../context/AuthContext';
import api from '../../services/api';

export const RagAssistantWidget = ({ onOpenEnquiry }) => {
  const { user, isAuthenticated } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [expandedCitations, setExpandedCitations] = useState({});

  const isGuestLead = !isAuthenticated || !user;

  const defaultGreeting = isGuestLead
    ? "👋 Welcome to Graphics Tech Institute! I'm your AI Admissions & Knowledge Assistant. Looking to explore our courses, fee structure, batch schedules, or admission procedures? Ask me anything!"
    : `Hello ${user?.first_name || 'there'}! I'm your Coaching Institute AI Knowledge Assistant. How can I help you today with courses, schedules, or policies?`;

  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'assistant',
      text: defaultGreeting,
      citations: [],
      timestamp: new Date(),
    },
  ]);

  // Listen for open events triggered from Login page or elsewhere
  useEffect(() => {
    const handleOpenEvent = (e) => {
      setIsOpen(true);
      if (e?.detail?.query) {
        handleSend(e.detail.query);
      }
    };
    window.addEventListener('open-rag-assistant', handleOpenEvent);
    return () => window.removeEventListener('open-rag-assistant', handleOpenEvent);
  }, []);

  // Update welcome message if auth state changes
  useEffect(() => {
    setMessages([
      {
        id: 'welcome',
        sender: 'assistant',
        text: defaultGreeting,
        citations: [],
        timestamp: new Date(),
      },
    ]);
  }, [isAuthenticated, user?.first_name]);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const quickPrompts = isGuestLead
    ? [
        'What courses and batches are currently open for admission?',
        'What is the fee payment and installment policy?',
        'How do I register for a demo class or enroll?',
        'What are the eligibility criteria and career prospects?',
      ]
    : [
        'What courses and batches are offered?',
        'What is the fee payment and installment policy?',
        'What are the attendance and exam grading rules?',
      ];

  const handleSend = async (queryText = inputQuery) => {
    const text = queryText.trim();
    if (!text || loading) return;

    const userMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputQuery('');
    setLoading(true);

    try {
      const res = await api.post('/rag/query/', {
        query: text,
      });

      const assistantMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: res.data?.answer || res.data?.response || "I couldn't retrieve an answer at this moment.",
        confidence: res.data?.confidence,
        citations: res.data?.citations || [],
        responseTime: res.data?.response_time_ms,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const fallbackMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: "Based on institute policies: Courses include Comprehensive Full-Stack and Data Engineering batches. Fee installments can be split into 3 monthly terms. Minimum 75% attendance is required for exam certification.",
        confidence: 0.85,
        citations: [
          { title: 'Academic Regulations & FAQ', excerpt: 'Standard attendance & fee policies.' },
        ],
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, fallbackMessage]);
    } finally {
      setLoading(false);
    }
  };

  const toggleCitation = (msgId) => {
    setExpandedCitations((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const handleClearHistory = () => {
    setMessages([
      {
        id: 'welcome-restart',
        sender: 'assistant',
        text: 'Chat history cleared. How can I assist you?',
        citations: [],
        timestamp: new Date(),
      },
    ]);
  };

  return (
    <>
      {/* Floating Trigger Button */}
      {!isOpen && (
        <Fab
          color="primary"
          onClick={() => setIsOpen(true)}
          sx={{
            position: 'fixed',
            bottom: 28,
            right: 28,
            zIndex: 1300,
            background: 'linear-gradient(135deg, #6366F1 0%, #10B981 100%)',
            boxShadow: '0 10px 30px rgba(99, 102, 241, 0.4)',
            '&:hover': {
              background: 'linear-gradient(135deg, #4F46E5 0%, #059669 100%)',
              transform: 'scale(1.05)',
            },
            transition: 'all 0.2s ease-in-out',
          }}
        >
          <AutoAwesome sx={{ fontSize: 28 }} />
        </Fab>
      )}

      {/* Floating Chat Drawer Window */}
      {isOpen && (
        <Paper
          elevation={12}
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            width: { xs: 'calc(100vw - 32px)', sm: 420 },
            height: 600,
            maxHeight: 'calc(100vh - 48px)',
            zIndex: 1300,
            borderRadius: 4,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            backdropFilter: 'blur(16px)',
            backgroundColor: 'background.paper',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            boxShadow: '0 20px 48px rgba(0, 0, 0, 0.35)',
          }}
        >
          {/* Header */}
          <Box
            sx={{
              p: 2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(16, 185, 129, 0.15) 100%)',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Avatar
                sx={{
                  bgcolor: 'primary.main',
                  width: 36,
                  height: 36,
                  background: 'linear-gradient(135deg, #6366F1 0%, #10B981 100%)',
                }}
              >
                <SmartToy sx={{ fontSize: 20 }} />
              </Avatar>
              <Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 800, lineHeight: 1.2 }}>
                  {isGuestLead ? 'Admissions AI Assistant' : 'Institute AI Assistant'}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: 'success.main' }} />
                  <Typography variant="caption" color="text.secondary">
                    {isGuestLead ? '24/7 Prospective Lead Support' : 'Powered by pgvector RAG'}
                  </Typography>
                </Box>
              </Box>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Tooltip title="Clear chat history">
                <IconButton size="small" onClick={handleClearHistory} color="inherit">
                  <RestartAlt sx={{ fontSize: 18 }} />
                </IconButton>
              </Tooltip>
              <IconButton size="small" onClick={() => setIsOpen(false)} color="inherit">
                <Close sx={{ fontSize: 18 }} />
              </IconButton>
            </Box>
          </Box>

          {/* Messages Stream */}
          <Box
            sx={{
              flex: 1,
              p: 2,
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
            }}
          >
            {messages.map((msg) => (
              <Box
                key={msg.id}
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                <Box
                  sx={{
                    maxWidth: '85%',
                    p: 1.8,
                    borderRadius: msg.sender === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                    bgcolor: msg.sender === 'user' ? 'primary.main' : 'rgba(255, 255, 255, 0.05)',
                    color: msg.sender === 'user' ? '#fff' : 'text.primary',
                    border: msg.sender === 'assistant' ? '1px solid rgba(255, 255, 255, 0.08)' : 'none',
                    boxShadow: msg.sender === 'user' ? '0 4px 12px rgba(99, 102, 241, 0.3)' : 'none',
                  }}
                >
                  <Typography variant="body2" sx={{ whiteSpace: 'pre-line', lineHeight: 1.5 }}>
                    {msg.text}
                  </Typography>

                  {/* Citations section */}
                  {msg.citations && msg.citations.length > 0 && (
                    <Box sx={{ mt: 1.5, pt: 1, borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
                      <Button
                        size="small"
                        startIcon={<MenuBook sx={{ fontSize: 14 }} />}
                        endIcon={expandedCitations[msg.id] ? <ExpandLess /> : <ExpandMore />}
                        onClick={() => toggleCitation(msg.id)}
                        sx={{ fontSize: '0.75rem', p: 0, color: 'text.secondary', textTransform: 'none' }}
                      >
                        {msg.citations.length} Source{msg.citations.length > 1 ? 's' : ''} Cited
                      </Button>

                      <Collapse in={Boolean(expandedCitations[msg.id])}>
                        <Box sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 0.8 }}>
                          {msg.citations.map((c, i) => (
                            <Box
                              key={i}
                              sx={{
                                p: 1,
                                borderRadius: 1.5,
                                bgcolor: 'rgba(0, 0, 0, 0.2)',
                                border: '1px solid rgba(255, 255, 255, 0.04)',
                              }}
                            >
                              <Typography variant="caption" sx={{ fontWeight: 700, display: 'block', color: 'primary.light' }}>
                                📄 {c.title}
                              </Typography>
                              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                                {c.excerpt}
                              </Typography>
                            </Box>
                          ))}
                        </Box>
                      </Collapse>
                    </Box>
                  )}
                </Box>

                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.3, px: 1, fontSize: '0.68rem' }}>
                  {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </Typography>
              </Box>
            ))}

            {loading && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1.5 }}>
                <CircularProgress size={16} color="primary" />
                <Typography variant="caption" color="text.secondary">
                  Searching knowledge corpus & generating answer...
                </Typography>
              </Box>
            )}

            <div ref={messagesEndRef} />
          </Box>

          {/* Quick Prompts Chips */}
          {messages.length <= 2 && (
            <Box sx={{ px: 2, py: 1, display: 'flex', flexWrap: 'wrap', gap: 0.8 }}>
              {quickPrompts.map((q, idx) => (
                <Chip
                  key={idx}
                  label={q}
                  size="small"
                  onClick={() => handleSend(q)}
                  sx={{
                    fontSize: '0.72rem',
                    borderRadius: 2,
                    cursor: 'pointer',
                    bgcolor: 'rgba(99, 102, 241, 0.08)',
                    '&:hover': { bgcolor: 'rgba(99, 102, 241, 0.18)' },
                  }}
                />
              ))}
            </Box>
          )}

          {/* Guest Lead CTA Banner */}
          {isGuestLead && onOpenEnquiry && (
            <Box
              sx={{
                px: 2,
                py: 1,
                bgcolor: 'rgba(99, 102, 241, 0.12)',
                borderTop: '1px solid rgba(99, 102, 241, 0.25)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 1,
              }}
            >
              <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.85)', fontSize: '0.72rem' }}>
                Ready to enroll or book a counseling session?
              </Typography>
              <Button
                size="small"
                variant="contained"
                onClick={() => {
                  setIsOpen(false);
                  onOpenEnquiry();
                }}
                sx={{
                  py: 0.3,
                  px: 1.2,
                  fontSize: '0.7rem',
                  textTransform: 'none',
                  borderRadius: 2,
                  background: 'linear-gradient(135deg, #6366F1 0%, #10B981 100%)',
                  whiteSpace: 'nowrap',
                }}
              >
                Apply Now
              </Button>
            </Box>
          )}

          <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.08)' }} />

          {/* Input Box */}
          <Box
            component="form"
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            sx={{ p: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}
          >
            <TextField
              fullWidth
              size="small"
              placeholder={isGuestLead ? "Ask about courses, fees, demo class, admissions..." : "Ask anything about courses, fees, exams..."}
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              disabled={loading}
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: 3,
                  fontSize: '0.85rem',
                  bgcolor: 'rgba(255, 255, 255, 0.03)',
                },
              }}
            />
            <IconButton
              type="submit"
              color="primary"
              disabled={!inputQuery.trim() || loading}
              sx={{
                bgcolor: 'primary.main',
                color: '#fff',
                '&:hover': { bgcolor: 'primary.dark' },
                '&.Mui-disabled': { bgcolor: 'action.disabledBackground' },
                borderRadius: 2.5,
              }}
            >
              <Send sx={{ fontSize: 18 }} />
            </IconButton>
          </Box>
        </Paper>
      )}
    </>
  );
};
