# Milestone 6 Security Checklist

- [ ] Supabase asymmetric signing key active hai.
- [ ] Email/site redirect allow-list correct hai.
- [ ] New signup `pending` hota hai.
- [ ] Custom access token hook enabled hai.
- [ ] `user_roles` and audit RLS/grants verified hain.
- [ ] Service-role key only auth-service environment mein hai.
- [ ] Service-role key ka `VITE_` variable nahi hai.
- [ ] Access/refresh tokens logs, URLs and error bodies mein nahi hain.
- [ ] Wrong issuer/audience/algorithm/signature tests pass hain.
- [ ] 401 and 403 behaviour tests pass hain.
- [ ] WebSocket ticket tamper/replay/expiry tests pass hain.
- [ ] Fusion/Feedback host ports secured Compose mein publish nahi hain.
- [ ] Default-deny RBAC review complete hai.
- [ ] First-admin bootstrap manually controlled hai.
- [ ] Multi-patient isolation limitation stakeholders ko clear hai.
