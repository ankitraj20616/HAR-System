# Authentication aur RBAC ko Easy Hinglish mein Samjho

## Authentication vs authorization

Authentication ka question hai: **"Aap kaun ho?"** Login aur JWT iska answer dete hain.

Authorization/RBAC ka question hai: **"Aapko kya karne ki permission hai?"** Caregiver alert acknowledge kar sakta hai, doctor history review kar sakta hai, admin role assign kar sakta hai.

## Do tokens kyun milte hain?

Access token short-time ID card hai. React ise HAR API request mein dikhata hai. Refresh token ID card renew karne wali private slip hai; ise HAR backend ko nahi dena, Supabase SDK manage karta hai.

## JWT verify ka simple example

Supabase token par digital signature lagata hai. Auth Service Supabase ki public JWKS key se signature check karti hai. Public key sirf verify kar sakti hai, fake token sign nahi kar sakti. Service expiry, correct project issuer, audience, user ID, session ID and role bhi check karti hai.

## `pending` role kyun?

Agar signup ke turant baad caregiver access mil jaye, koi unknown person account bana kar monitoring data dekh sakta hai. Isliye default `pending`: account valid hai but data permission nahi. Admin approval least-privilege rule follow karta hai.

## Refresh token backend ko kyun nahi bhejte?

Refresh token long-lived session renew karta hai. Har service tak bhejne se leak surface badhta hai. React/Supabase ke paas rakhna simpler and safer hai. HAR backend ko sirf short-lived access JWT chahiye.

## WebSocket ticket kya hai?

Normal fetch header mein JWT bhej sakta hai, browser WebSocket custom Authorization header easily nahi bhejta. JWT URL mein dena logs mein leak kar sakta hai. React pehle JWT-secured REST request se 30-second one-time ticket leta hai, phir ticket se WebSocket kholta hai.

## 401 aur 403 difference

- 401: token missing, fake, wrong project ya expired—identity prove nahi hui.
- 403: identity valid hai, but role ko requested action allowed nahi.

## Current limitation

RBAC batata hai kaunsa role kaunsa action kar sakta hai. Current demo single monitored context hai. Multiple patient deployment mein records par `patient_id` aur caregiver/doctor assignment checks separately add karne honge.
