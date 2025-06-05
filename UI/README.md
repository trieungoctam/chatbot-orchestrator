# Healthcare AI Assistant - Frontend UI

A modern, responsive web interface for healthcare chatbot interactions with comprehensive admin dashboard.

## 🚀 Quick Start

### Option 1: Simple File Opening
```bash
# Navigate to UI directory
cd UI

# Open chat interface
open index.html
# OR double-click index.html in file manager

# Open admin dashboard
open admin.html
# OR double-click admin.html in file manager
```

### Option 2: HTTP Server (Recommended)
```bash
# Navigate to UI directory
cd UI

# Start HTTP server (Python 3)
python3 -m http.server 8080

# Alternative: Node.js
npx http-server -p 8080

# Alternative: PHP
php -S localhost:8080
```

Then open:
- **Chat Interface**: http://localhost:8080/index.html
- **Admin Dashboard**: http://localhost:8080/admin.html

## 📱 Responsive Design Testing

### Breakpoints
The UI uses the following responsive breakpoints:

| Breakpoint | Width | Target Devices |
|------------|-------|----------------|
| Mobile Small | ≤ 480px | Small phones |
| Mobile Large | ≤ 768px | Phones, small tablets |
| Tablet | ≤ 1024px | Tablets, small laptops |
| Desktop | > 1024px | Laptops, desktops |

### Testing Methods

#### 1. Browser Developer Tools
```bash
# Chrome/Edge/Firefox
F12 → Toggle Device Toolbar (Ctrl+Shift+M)

# Test these device presets:
- iPhone SE (375×667)
- iPhone 12 Pro (390×844)
- iPad (768×1024)
- iPad Pro (1024×1366)
- Desktop (1920×1080)
```

#### 2. Physical Device Testing
```bash
# Start server accessible from network
python3 -m http.server 8080 --bind 0.0.0.0

# Find your IP address
ip addr show    # Linux
ipconfig        # Windows
ifconfig        # macOS

# Access from mobile: http://YOUR_IP:8080/index.html
```

#### 3. Browser Window Resizing
- Manually resize browser window from 320px to 1920px width
- Check layout at each major breakpoint

### 📋 Responsive Checklist

#### Chat Interface (index.html)
- [ ] **Mobile ≤ 480px**
  - [ ] Header collapses to single column
  - [ ] Sidebar becomes horizontal scrollable conversation list
  - [ ] Quick actions stack vertically
  - [ ] Message bubbles max-width 90%
  - [ ] Input footer stacks vertically
  - [ ] Welcome icon scales down (60px)

- [ ] **Mobile ≤ 768px**
  - [ ] Main content becomes vertical layout
  - [ ] Sidebar height reduced to 200px
  - [ ] Conversation list becomes horizontal scroll
  - [ ] Message bubbles max-width 85%
  - [ ] Modal width 95% with margins
  - [ ] Input padding reduced

- [ ] **Tablet ≤ 1024px**
  - [ ] Dashboard grids collapse to single column
  - [ ] Charts maintain aspect ratio
  - [ ] Navigation remains functional

- [ ] **Desktop > 1024px**
  - [ ] Full sidebar layout (320px width)
  - [ ] Two-column grid layouts
  - [ ] Optimal spacing and typography

#### Admin Dashboard (admin.html)
- [ ] **Mobile ≤ 480px**
  - [ ] Admin content padding reduced
  - [ ] Cards padding reduced
  - [ ] Metrics grid single column
  - [ ] Modal 95% width with margins

- [ ] **Mobile ≤ 768px**
  - [ ] Sidebar moves to bottom
  - [ ] Main content on top
  - [ ] Section headers stack vertically
  - [ ] Search inputs full width
  - [ ] Table font size reduced
  - [ ] Table padding reduced

- [ ] **Tablet ≤ 1024px**
  - [ ] All grids single column
  - [ ] Chart cards span full width
  - [ ] Monitoring grids stack
  - [ ] Settings grids stack

- [ ] **Desktop > 1024px**
  - [ ] Full sidebar navigation (280px)
  - [ ] Multi-column grids
  - [ ] Optimal table layouts

### 🎨 Design Features

#### Chat Interface
- **Layout**: Flexbox-based responsive design
- **Sidebar**: Collapsible conversation management
- **Messages**: Auto-resizing bubbles with timestamps
- **Input**: Auto-expanding textarea with character counter
- **Modals**: Centered with backdrop blur
- **Quick Actions**: Grid layout with healthcare icons

#### Admin Dashboard
- **Navigation**: Collapsible sidebar with sections
- **Dashboard**: Card-based metrics display
- **Charts**: Responsive Chart.js visualizations
- **Tables**: Sortable with action buttons
- **Forms**: Grouped settings with validation
- **Monitoring**: Real-time metrics and health indicators

### 🔧 Customization

#### Colors (CSS Variables)
```css
:root {
  --primary-color: #2563eb;        /* Blue */
  --secondary-color: #059669;      /* Green */
  --success-color: #10b981;        /* Success */
  --warning-color: #f59e0b;        /* Warning */
  --error-color: #ef4444;          /* Error */
}
```

#### Breakpoints
```css
/* Tablet */
@media (max-width: 1024px) { }

/* Mobile Large */
@media (max-width: 768px) { }

/* Mobile Small */
@media (max-width: 480px) { }
```

#### Spacing Scale
```css
--spacing-1: 0.25rem;   /* 4px */
--spacing-2: 0.5rem;    /* 8px */
--spacing-3: 0.75rem;   /* 12px */
--spacing-4: 1rem;      /* 16px */
--spacing-6: 1.5rem;    /* 24px */
--spacing-8: 2rem;      /* 32px */
```

### 🎯 Testing Scenarios

#### Functional Testing
1. **Chat Interface**
   - [ ] Send messages on all screen sizes
   - [ ] Open/close settings modal
   - [ ] Navigate between conversations
   - [ ] Use quick action buttons
   - [ ] Test bot selector dropdown

2. **Admin Dashboard**
   - [ ] Navigate between sections
   - [ ] Create new bot (modal)
   - [ ] View charts and metrics
   - [ ] Use table filters
   - [ ] Export functionality

#### Visual Testing
1. **Typography**
   - [ ] Text remains readable at all sizes
   - [ ] Proper line spacing maintained
   - [ ] No text overflow

2. **Layouts**
   - [ ] No horizontal scrolling on mobile
   - [ ] Consistent spacing
   - [ ] Proper alignment

3. **Interactive Elements**
   - [ ] Buttons remain clickable (min 44px)
   - [ ] Form inputs accessible
   - [ ] Hover states work

### 🌙 Dark Mode Support
Automatic dark mode detection via `prefers-color-scheme`:
```css
@media (prefers-color-scheme: dark) {
  /* Dark theme variables */
}
```

### 🔍 Debugging Tips

#### CSS Grid Inspector
```bash
# Chrome DevTools
F12 → Elements → Grid overlay
```

#### Responsive Issues
```bash
# Common fixes
- Check viewport meta tag
- Verify CSS media queries
- Test flex/grid properties
- Check min/max-width values
```

#### Performance
```bash
# Test loading on slow connections
DevTools → Network → Slow 3G
```

### 📊 Browser Support
- **Modern browsers**: Chrome 80+, Firefox 75+, Safari 13+, Edge 80+
- **Mobile**: iOS Safari 13+, Android Chrome 80+
- **Features**: CSS Grid, Flexbox, CSS Variables

### 🚀 Deployment
```bash
# Build for production
# (No build step required - vanilla HTML/CSS/JS)

# Deploy to static hosting
- Netlify: drag UI folder
- Vercel: vercel UI/
- GitHub Pages: push to gh-pages branch
- AWS S3: sync UI folder

# Configure API endpoint in settings
# Update chat-app.js and admin-app.js:
apiEndpoint: 'https://your-api-domain.com'
```

## 🔗 Integration

### Backend API
Configure in Settings or directly in JavaScript:
- **Chat API**: `/api/v1/chat/message`
- **Admin API**: `/api/v1/admin/*`
- **Auth**: X-API-KEY header

### Features
- Real-time messaging
- Conversation management
- Bot administration
- System monitoring
- Export functionality
- Responsive design
- Dark mode support