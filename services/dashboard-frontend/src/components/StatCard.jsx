const StatCard = ({ title, value, change, icon: Icon, color }) => {
  return (
    <div className="glass-panel" style={{ padding: '24px', flex: 1 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
        <div style={{ 
          padding: '10px', 
          borderRadius: '12px', 
          backgroundColor: `rgba(${color}, 0.1)`,
          color: `rgb(${color})`
        }}>
          <Icon size={24} />
        </div>
        <span style={{ 
          fontSize: '0.875rem', 
          color: change.startsWith('+') ? 'var(--accent-green)' : 'var(--accent-red)',
          fontWeight: 600
        }}>
          {change}
        </span>
      </div>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '4px' }}>{title}</p>
      <h3 style={{ fontSize: '1.75rem', color: '#fff' }}>{value}</h3>
    </div>
  );
};

export default StatCard;
