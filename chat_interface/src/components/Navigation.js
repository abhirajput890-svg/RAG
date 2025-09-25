import React from 'react';
import { useAuth } from '../Context/AuthContext';

const Navigation = () => {
  const { logout, user } = useAuth();

  return (
    <nav className="navbar">
      <div className="nav-brand">
        <h2>RAG Chatbot</h2>
      </div>
      <div className="nav-user">
        <span>Welcome, {user?.username}</span>
        <button onClick={logout} className="logout-btn">Logout</button>
      </div>
    </nav>
  );
};

export default Navigation;
