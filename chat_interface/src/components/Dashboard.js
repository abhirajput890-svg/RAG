import React, { useState } from 'react';
import TextQuery from './TextQuery';
import FileUpload from './FileUpload';
import BatchUpload from './BatchUpload';
import "../Styles/Dashboard.css";

const Dashboard = () => {
  const [activeTab, setActiveTab] = useState('text');

  const tabs = [
    { id: 'text', label: 'Text Query', component: TextQuery },
    { id: 'file', label: 'Image Upload', component: FileUpload },
    { id: 'batch', label: 'Batch Upload', component: BatchUpload },
  ];

  const ActiveComponent = tabs.find(tab => tab.id === activeTab)?.component;

  return (
    <div className="dashboard-container">
      <div className="dashboard-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      
      <div className="dashboard-content">
        {ActiveComponent && <ActiveComponent />}
      </div>
    </div>
  );
};

export default Dashboard;
