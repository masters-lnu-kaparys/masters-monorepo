/**
 * Auth0 Post Login Action
 *
 * What it does:
 * 1. Assigns the default "User" role to new accounts that still have no roles.
 * 2. Copies the effective roles into both ID token and access token.
 *
 * Required Action secrets:
 * - domain
 * - clientId
 * - clientSecret
 * - defaultUserRoleId
 * - defaultUserRoleName
 */
exports.onExecutePostLogin = async (event, api) => {
  const namespace = "https://masters.api";
  const { ManagementClient } = require("auth0");

  let effectiveRoles = event.authorization?.roles ?? [];

  if (effectiveRoles.length === 0) {
    const management = new ManagementClient({
      domain: event.secrets.domain,
      clientId: event.secrets.clientId,
      clientSecret: event.secrets.clientSecret,
    });

    await management.users.assignRoles(
      { id: event.user.user_id },
      { roles: [event.secrets.defaultUserRoleId] },
    );

    effectiveRoles = [event.secrets.defaultUserRoleName || "User"];
  }

  api.idToken.setCustomClaim(`${namespace}/roles`, effectiveRoles);
  api.accessToken.setCustomClaim(`${namespace}/roles`, effectiveRoles);
};
