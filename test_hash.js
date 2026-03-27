const crypto = require('crypto');
function generatePIN(secret, offsetMinutes = 0) {
  const windowMs = 15 * 60 * 1000;
  const timeWindow = Math.floor((Date.now() + (offsetMinutes * 60 * 1000)) / windowMs);
  const hash = crypto.createHmac('sha256', secret)
    .update(timeWindow.toString())
    .digest('hex');
  const pin = parseInt(hash.substring(0, 8), 16) % 1000000;
  return {pin: pin.toString().padStart(6, '0'), timeWindow, hash: hash.substring(0, 8)};
}
console.log(generatePIN('8698638609:AAEaE1oKl1307vB11rOK_RoDniiAm2BeELY', 0));
