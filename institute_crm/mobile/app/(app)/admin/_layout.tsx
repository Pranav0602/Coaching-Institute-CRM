import React from 'react';

import { PersonaTabs } from '@/navigation/PersonaTabs';
import { useAuth } from '@/context/AuthContext';

const AdminLayout = () => {
  const { role } = useAuth();
  return <PersonaTabs role={role} />;
};

export default AdminLayout;
