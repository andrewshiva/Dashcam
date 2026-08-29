import { LayoutDashboard, Map, FileText, Settings, Shield, Activity, BarChart3 } from 'lucide-react';

const Sidebar = ({ currentView, onViewChange = () => {} }) => {
  const menuItems = [
    { icon: LayoutDashboard, label: 'Overview', id: 'overview' },
    { icon: Map, label: 'Defect Map', id: 'map' },
    { icon: BarChart3, label: 'Analytics', id: 'analytics' },
    { icon: FileText, label: 'Reports', id: 'reports' },
    { icon: Shield, label: 'Security', id: 'security' },
    { icon: Activity, label: 'System Health', id: 'health' },
  ];

  return (
    <aside style={{
      width: '220px',
      minHeight: '100vh',
      padding: '20px 18px',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
      borderRight: '1px solid var(--border-color)',
      backgroundColor: 'var(--bg-card)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '28px' }}>
        <div style={{
          width: '28px',
          height: '28px',
          background: 'linear-gradient(135deg, var(--accent-blue), var(--accent-green))',
          borderRadius: '8px'
        }}></div>
        <div>
          <h2 style={{ fontSize: '1.12rem', color: 'var(--text-primary)', lineHeight: 1.1 }}>DashcamR</h2>
        </div>
      </div>

      <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {menuItems.map((item) => (
          <div 
            key={item.id} 
            onClick={() => onViewChange(item.id)}
            className={`sidebar-menu-item ${currentView === item.id ? 'active' : ''}`}
          >
            <item.icon size={18} />
            <span style={{ fontWeight: 500 }}>{item.label}</span>
          </div>
        ))}
      </nav>

      <div style={{ marginTop: '18px', paddingTop: '18px', borderTop: '1px solid var(--border-color)' }}>
        <div className="sidebar-menu-item">
          <Settings size={18} />
          <span>Settings</span>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
