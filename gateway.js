const express = require('express');
const jwt = require('jsonwebtoken');
const bodyParser = require('body-parser');
const cors = require('cors');

const app = express();
const port = 3000;
const secretKey = 'your_secret_key'; // Change this to a strong secret key.

app.use(cors());
app.use(bodyParser.json());

// Mock database
let devices = [
    { id: 1, type: 'lamp', state: 'off' },
    { id: 2, type: 'fan', state: 'on' },
];

let connectionHistory = [];
let onlineUsers = [];

// Middleware for authentication
function authenticateToken(req, res, next) {
    const token = req.headers['authorization']?.split(' ')[1];
    if (!token) return res.status(401).send('Access Denied');

    jwt.verify(token, secretKey, (err, user) => {
        if (err) return res.status(403).send('Invalid Token');
        req.user = user;
        next();
    });
}

// Login endpoint
app.post('/login', (req, res) => {
    const { username, password } = req.body;
    // Mock user validation
    if (username === 'admin' && password === 'password') {
        const token = jwt.sign({ username }, secretKey, { expiresIn: '1h' });
        onlineUsers.push(username);
        connectionHistory.push({ user: username, date: new Date().toISOString() });
        res.json({ token });
    } else {
        res.status(401).send('Invalid Credentials');
    }
});

// Get devices
app.get('/devices', authenticateToken, (req, res) => {
    res.json(devices);
});

// Toggle device state
app.post('/devices/:id/toggle', authenticateToken, (req, res) => {
    const device = devices.find((d) => d.id === parseInt(req.params.id));
    if (!device) return res.status(404).send('Device not found');

    device.state = device.state === 'on' ? 'off' : 'on';
    res.json(device);
});

// Get statistics
app.get('/statistics', authenticateToken, (req, res) => {
    res.json({
        totalDevices: devices.length,
        deviceDetails: devices,
        connectionHistory,
        onlineUsers,
    });
});

// Logout endpoint
app.post('/logout', authenticateToken, (req, res) => {
    onlineUsers = onlineUsers.filter((user) => user !== req.user.username);
    res.send('Logged out successfully');
});

app.listen(port, () => console.log(`Server running on http://localhost:${port}`));
