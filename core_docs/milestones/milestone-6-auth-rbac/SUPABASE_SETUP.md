# Supabase Setup: Step-by-Step Easy Guide

## 1. Project and keys

Supabase project create/open karo. Project URL and **publishable key** copy karo. Backend role administration ke liye service-role key copy karo; is key ko password jaisa secret rakho.

`.env.example` ko `.env` copy karke values set karo. `AUTH_TICKET_SECRET` ke liye random 32+ character string use karo. `.env` commit mat karo.

## 2. Asymmetric JWT signing key

Supabase Authentication signing-key page par asymmetric RSA/EC key active rakho. Auth Service JWKS public keys se verify karti hai; legacy shared JWT secret expected design nahi hai.

Key rotate karte waqt Supabase recommended standby/cache window follow karo. Immediate rotation old/new cached key mismatch create kar sakti hai.

## 3. SQL migration

Supabase SQL Editor mein `supabase/migrations/001_auth_rbac.sql` complete run karo. Ye roles, audit log, new-user trigger and custom-token hook function banata hai.

## 4. Enable hook

Dashboard → Authentication → Hooks → Custom Access Token mein `public.custom_access_token_hook` select and enable karo.

Hook enable hone ke baad user logout/login ya session refresh kare. JWT mein `user_role` claim visible hona chahiye. Real token ko screenshots, tickets or logs mein paste mat karo.

## 5. Email settings

Authentication URL Configuration mein dashboard Site URL and allowed redirect URLs set karo. Email confirmation development/demo requirement ke hisaab se enable rakho. Confirmation enabled ho to signup response mein session null hona normal hai.

## 6. First admin bootstrap

1. Normal UI se first account signup and email verify karo.
2. Supabase Table Editor mein `user_roles` kholo.
3. Us user ka role `pending` se `admin` karo.
4. User logout/login kare.
5. Iske baad admin panel se other user UUID roles assign kar sakta hai.

First admin bootstrap ko public API se automatic mat karo; warna attacker first admin ban sakta hai.

## 7. Start and check

`docker compose config` se required environment validate karo, phir `docker compose up --build`. Browser signup → email confirmation → pending → admin assignment → re-login flow check karo.
