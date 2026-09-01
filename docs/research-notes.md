# Research notes - Ruijie Reyee NBS3200 (web RPC, injection attempts, dead ends)

Everything below was verified against a live RG-NBS3200-48GT4XS on ReyeeOS
2.390.1.1823 (SWITCH_3.0(1)B11P390) unless marked otherwise.

## Web RPC surface

Base: `https://<ip>/cgi-bin/luci/`.

Login flow:
1. `GET /cgi-bin/luci/` -> extract AES key from
   `GibberishAES.enc(passwordEl.value, "<hex>")` (rotates per render; server
   keeps the last one per source IP - fetch page and log in immediately).
2. `POST /cgi-bin/luci/api/auth` with
   `{method:"login", params:{username:"admin", time:<unix>, encry:true,
   pwd:<GibberishAES.enc(pass,key)>, isCheckReadAgreement:"true"}}`
   -> returns `sid`. The session cookie name is the device SN.
3. Calls: `POST /cgi-bin/luci/api/cmd?auth=<sid>` with anti-bot headers
   `Content-Accept: md5("Web@Rj$2020!" + byteLen(body))` and
   `Contents-Accept: md5("Web@Rj$2020!" + body)`, body
   `{method:"devSta.get|devConfig.get|devSta.set|...", params:{module:"<mod>"}}`.

Other endpoints (plain JSON-RPC 2.0 with `id`, session cookie, NO md5 headers):
- `/cgi-bin/luci/api/diagnose` - methods `ping`, `traceroute`, `nslookup`
  with params `{type,count,size,ttl,target,ipType}`; output polled with
  `getDiagnoseRes`.
- `/cgi-bin/luci/api/system` - e.g. `getVersion {"deviceType":"self"}`.
- `/cgi-bin/luci/api/upload/upgradeLocal?auth=<sid>` - multipart firmware
  upload (field `file`, extra field `isPersist`).
- `/cgi-bin/luci/api/upload/restoreConfig?auth=<sid>` - config restore (.gz).
- `/cgi-bin/luci/api/download?auth=<sid>` - config backup (method
  `backupConfig`).

The full module->command map (~221 modules) lives in the web SPA
(`app*.js`). Useful verified modules: `sysinfo`, `port_info`, `port_base`,
`stp_port_status`, `rldp_port_status`, `vlan`, `lldp_nghbr`, `fiberPortInfo`,
`snmp`, `develop_mode`, `http_tool`, `multiuser`, `user_list`.

## Command injection attempts (all FAILED)

- `/api/diagnose` ping/traceroute/nslookup `target`: `;`, `|`, `&`,
  backticks, `$()`, `\n`, `\r` all rejected with `{"msg":"shell illegal"}`.
  A tab character passes the filter but the target is shell-quoted, so it
  does not break out of the ping command.
- `count`/`size`/`ttl` fields accept shell metacharacters (no "shell
  illegal") but are validated as numbers before reaching any shell.
- `hostName` set: rejected with "param is unsafe".
- `radius`/`radius_single` `detectServerName`: rejected ("radius param failed!").
- `dev_diag` (fault collection) accepts `{"user","action"}` but returns empty
  data; no file-download endpoint found for its `/tmp/dev_diag/result.json`.
- The MA3063 router trick `/__factory_verify_mode__` does NOT exist here (404).

## Firmware encryption

Official images (`..._with_boot_encrypto_v2.tar.gz` -> inner
`..._squashfs_sysupgrade_encrypto_v2.tar`):

- First line: `upgrade_crypt_v2!@2023`, then base64 of an OpenSSL
  `Salted__` blob.
- Key: `BR0khBR0khsHi4MkNGrJ421Yf&j8ceh6`, EVP_BytesToKey with MD5 iterated
  2023 times, AES-256-CBC. See `toolkit/reyee_toolkit.py` (`dec`).
- Older packages use `upgrade_crypt_v1!@2021` (raw binary, not base64).
- The `.md5` file inside the package oddly concatenates the magic with the
  file md5: `upgrade_crypt_v2!@2023<md5(ciphertext-file)>  <name>`.
  (Treating that as the passphrase does NOT work - the real key is above.)

## Developer-mode password

- `/usr/sbin/set-passwd` runs at every boot (`/etc/init.d/rg-passwd`,
  START=00) and sets the root password derived from the device serial:
  `md5(c1 + SN + c2)[:16]`. Verified by running the firmware binary under
  qemu-mips and by matching the live `/etc/shadow` hash
  (`openssl passwd -1` check).
- `/etc/config/dropbear`: Port 54133, PasswordAuth on, RootPasswordAuth on.
- Enabling developer mode only starts/restarts dropbear; the password is
  already set from boot.

## What finally worked

Decrypt the official 2.380 firmware -> extract squashfs -> run the real
`set-passwd` with qemu-mips against the device SN -> take the `"passed"` hex
string as the SSH password. No downgrade, no serial console needed.
