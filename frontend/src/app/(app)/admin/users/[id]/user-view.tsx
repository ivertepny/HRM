"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { PageHeader, Section } from "@/components/app/section";
import { fullName } from "@/components/app/user-name";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { canAnywhere } from "@/lib/access";
import { useUser } from "@/lib/admin-queries";
import { ApiError } from "@/lib/api/client";
import { formatDate } from "@/lib/format";
import { useMe, useMyAccess } from "@/lib/queries";

import { AccountSection } from "./account-section";
import { HireForm } from "./hire-form";
import { RolesSection } from "./roles-section";

export function UserView() {
  const { id } = useParams<{ id: string }>();
  const userId = Number(id);
  const user = useUser(userId);
  const me = useMe();
  const access = useMyAccess();
  const can = (codename: string) => canAnywhere(access.data, codename);

  if (user.isPending) {
    return <Skeleton className="h-12 w-80" aria-busy="true" />;
  }
  if (user.isError) {
    const notFound = user.error instanceof ApiError && user.error.status === 404;
    return (
      <div className="grid gap-4">
        <PageHeader title={notFound ? "Обліковий запис не знайдено" : "Не вдалося завантажити"} />
        <p className="text-slate">
          {notFound ? "Його немає або він поза вашою областю доступу." : user.error.message}{" "}
          <Link href="/admin/users" className="text-primary underline-offset-4 hover:underline">
            До облікових записів
          </Link>
        </p>
      </div>
    );
  }

  const data = user.data;
  const isSelf = data.id === me.data?.id;

  return (
    <div className="grid gap-10">
      <PageHeader title={fullName(data)}>
        {data.email}
        <span className="mt-1 block text-base">
          Створено {formatDate(data.created_at)}
          {data.last_login ? `, востаннє входив(-ла) ${formatDate(data.last_login)}` : ", ще не входив(-ла)"}
        </span>
      </PageHeader>

      <Section title="Обліковий запис">
        <AccountSection
          key={data.updated_at}
          user={data}
          isSelf={isSelf}
          canWrite={can("users:write")}
          canDelete={can("users:delete")}
        />
      </Section>

      {can("roles:read") && (
        <Section title="Ролі та доступ">
          <RolesSection
            userId={userId}
            canManage={can("roles:manage")}
            canPickUnit={can("company:read")}
          />
        </Section>
      )}

      <Section title="Працівник">
        {data.employee ? (
          <Link
            href={`/employees/${data.employee}`}
            className={buttonVariants({ variant: "outline" })}
          >
            Відкрити профіль працівника
          </Link>
        ) : can("employees:write") ? (
          <div className="grid gap-3">
            <p className="text-slate">Профіль працівника ще не оформлено.</p>
            <HireForm userId={userId} canSetSalary={can("salary:write")} />
          </div>
        ) : (
          <p className="text-slate">Профіль працівника ще не оформлено.</p>
        )}
      </Section>
    </div>
  );
}
