
## Single Sign On

Another django website is the primary identity provider and the mailing lists are the relying party.

This has been implemented. See other pages for details:  

https://github.com/cppalliance/ansible-mailman3/blob/master/docs/single-sign-in.md

https://github.com/cppalliance/Infrastructure-Docs/blob/master/mailman/lists-wg21-org/WG21-Universal-Login.md

## How it works

If a user visits wg21.org they may log in or log out, via a social provider (GitHub, Google) and that functions as normal. No modification.  

If a user visits the lists at lists.wg21.org and clicks Sign In, it communicates using OAuth to wg21.org and completes a sign-in automatically. If the user isn't yet logged into wg21.org, they are redirected there, and can choose how to log in. Then they will be redirected back to the lists. The user will not have a username/password on lists.wg21.org. They will get a user/social-account which links to wg21.org.  
