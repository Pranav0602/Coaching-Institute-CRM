import React from 'react';

import { PersonaTabs } from '@/navigation/PersonaTabs';
import { useAuth } from '@/context/AuthContext';

const CounsellorLayout = () => {
  const { role } = useAuth();
  return <PersonaTabs role={role} />;
};

export default CounsellorLayout;
