import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useAuth } from '@/components/auth/AuthProvider';
import { useOrganization } from '@/hooks/useOrganization';
import { useUser } from '@/hooks/useUser';
import { updateUser } from '@/api/users';
import { getMyMembership } from '@/api/memberships';
import { Button } from '@/components/ui/button';
import { SignOutButton } from '@/components/auth/SignOutButton';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

function normalizeOptionalText(value: string) {
  const trimmed = value.trim();
  if (trimmed.length === 0) {
    return null;
  }
  return trimmed;
}

export function Accounts() {
  const auth = useAuth();
  const { organization, organizationsQuery } = useOrganization();
  const { user, userQuery } = useUser();
  const activeOrganizationId = organization?.id ?? null;
  const userId = auth.user?.id ?? null;

  const membershipQuery = useQuery({
    queryKey: ['membership', activeOrganizationId],
    enabled:
      auth.isLoading === false &&
      auth.user !== null &&
      activeOrganizationId !== null,
    queryFn: async () => {
      if (!activeOrganizationId) {
        throw new Error('Missing organization id');
      }
      return getMyMembership(activeOrganizationId);
    },
  });

  const updateMutation = useMutation({
    mutationFn: async () => {
      if (!userId || !activeOrganizationId) {
        throw new Error('Missing user id');
      }
      return updateUser(activeOrganizationId, userId, payloadToSave);
    },
    onSuccess: async () => {
      await userQuery.refetch();
      setIsDirty(false);
    },
  });

  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [avatarUrl, setAvatarUrl] = useState('');
  const [isDirty, setIsDirty] = useState(false);

  const initialFormState = useMemo(() => {
    return {
      username: user?.username ?? '',
      full_name: user?.full_name ?? '',
      avatar_url: user?.avatar_url ?? '',
    };
  }, [user?.username, user?.full_name, user?.avatar_url]);

  useEffect(() => {
    setUsername(initialFormState.username);
    setFullName(initialFormState.full_name);
    setAvatarUrl(initialFormState.avatar_url);
    setIsDirty(false);
  }, [initialFormState]);

  const payloadToSave = useMemo(() => {
    const next = {
      username: normalizeOptionalText(username),
      full_name: normalizeOptionalText(fullName),
      avatar_url: normalizeOptionalText(avatarUrl),
    };

    const previous = {
      username: user?.username ?? null,
      full_name: user?.full_name ?? null,
      avatar_url: user?.avatar_url ?? null,
    };

    const payload: Record<string, unknown> = {};
    if (next.username !== previous.username) payload.username = next.username;
    if (next.full_name !== previous.full_name)
      payload.full_name = next.full_name;
    if (next.avatar_url !== previous.avatar_url)
      payload.avatar_url = next.avatar_url;
    return payload;
  }, [avatarUrl, fullName, username, user]);

  const cardStatus = useMemo((): {
    message: string;
    isError: boolean;
  } | null => {
    if (auth.isLoading) return { message: 'Loading session…', isError: false };
    if (!auth.user) return { message: 'You are not signed in.', isError: true };
    if (organizationsQuery.isLoading) {
      return { message: 'Loading organizations…', isError: false };
    }
    if (organizationsQuery.isError) {
      return { message: 'Failed to load organizations.', isError: true };
    }
    if (!activeOrganizationId) {
      return { message: 'No organization selected.', isError: false };
    }
    if (membershipQuery.isLoading) {
      return { message: 'Loading membership…', isError: false };
    }
    if (membershipQuery.isError) {
      return { message: 'Failed to load membership.', isError: true };
    }
    if (userQuery.isLoading) {
      return { message: 'Loading profile…', isError: false };
    }
    if (userQuery.isError) {
      return { message: 'Failed to load profile.', isError: true };
    }
    if (!user) return null;
    return null;
  }, [
    auth.isLoading,
    auth.user,
    activeOrganizationId,
    organizationsQuery.isLoading,
    organizationsQuery.isError,
    membershipQuery.isLoading,
    membershipQuery.isError,
    userQuery.isLoading,
    userQuery.isError,
    user,
  ]);

  const showForm = user != null && cardStatus === null;

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
          <CardDescription>
            View and update your profile details.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {cardStatus && (
            <p
              className={
                cardStatus.isError
                  ? 'text-sm text-destructive'
                  : 'text-sm text-muted-foreground'
              }
            >
              {cardStatus.message}
            </p>
          )}
          {showForm && (
            <>
              <div className="grid gap-2">
                <Label>Organization</Label>
                <p className="text-sm text-muted-foreground">
                  {organization?.name ?? 'Unknown'}
                </p>
                <p className="text-sm text-muted-foreground break-all">
                  {activeOrganizationId}
                </p>
              </div>

              <div className="grid gap-2">
                <Label>Membership</Label>
                <p className="text-sm text-muted-foreground">
                  Role: {membershipQuery.data?.role ?? 'Unknown'}
                </p>
                <p className="text-sm text-muted-foreground break-all">
                  {membershipQuery.data?.id ?? 'Unknown'}
                </p>
              </div>

              <div className="grid gap-2">
                <Label>Id</Label>
                <p className="text-sm text-muted-foreground break-all">
                  {user.id}
                </p>
              </div>

              <div className="grid gap-2">
                <Label>Created</Label>
                <p className="text-sm text-muted-foreground">
                  {user.created_at}
                </p>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="username">Username</Label>
                <Input
                  id="username"
                  value={username}
                  onChange={(value) => {
                    setUsername(value);
                    setIsDirty(true);
                  }}
                  placeholder="yourname"
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="full_name">Full name</Label>
                <Input
                  id="full_name"
                  value={fullName}
                  onChange={(value) => {
                    setFullName(value);
                    setIsDirty(true);
                  }}
                  placeholder="Jane Doe"
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="avatar_url">Avatar URL</Label>
                <Input
                  id="avatar_url"
                  type="url"
                  value={avatarUrl}
                  onChange={(value) => {
                    setAvatarUrl(value);
                    setIsDirty(true);
                  }}
                  placeholder="https://…"
                />
              </div>

              {updateMutation.isError && (
                <p className="text-sm text-destructive">
                  Failed to save changes.
                </p>
              )}
              {updateMutation.isSuccess && (
                <p className="text-sm text-muted-foreground">Saved.</p>
              )}
            </>
          )}
        </CardContent>
        <CardFooter className="justify-between">
          <SignOutButton scope="local" />
          <Button
            isDisabled={
              !user ||
              updateMutation.isPending ||
              isDirty === false ||
              Object.keys(payloadToSave).length === 0
            }
            onClick={() => {
              updateMutation.mutate();
            }}
          >
            {updateMutation.isPending ? 'Saving…' : 'Save'}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
