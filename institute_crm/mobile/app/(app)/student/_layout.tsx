import React from 'react';

import { PersonaTabs } from '@/navigation/PersonaTabs';
import { useAuth } from '@/context/AuthContext';

const StudentLayout = () => {
  const { role } = useAuth();
  return <PersonaTabs role={role} />;
};

export default StudentLayout;
