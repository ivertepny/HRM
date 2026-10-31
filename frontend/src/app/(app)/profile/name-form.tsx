"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, type Schemas } from "@/lib/api/client";
import { useUpdateMe } from "@/lib/queries";

const schema = z.object({
  first_name: z.string().trim().min(1, "Вкажіть ім'я").max(255),
  last_name: z.string().trim().min(1, "Вкажіть прізвище").max(255),
});

type Values = z.infer<typeof schema>;

export function NameForm({ user }: { user: Schemas["User"] }) {
  const update = useUpdateMe();
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isDirty },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { first_name: user.first_name ?? "", last_name: user.last_name ?? "" },
  });

  function onSubmit(values: Values) {
    update.mutate(values, {
      onSuccess: (saved) => {
        reset({ first_name: saved.first_name ?? "", last_name: saved.last_name ?? "" });
        toast.success("Зміни збережено");
      },
      onError: (error) => {
        if (error instanceof ApiError) {
          for (const [field, message] of Object.entries(error.fieldErrors)) {
            if (field in values) setError(field as keyof Values, { message });
          }
        }
        toast.error(error.message);
      },
    });
  }

  const fields = [
    ["first_name", "Ім'я", "given-name"],
    ["last_name", "Прізвище", "family-name"],
  ] as const;

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="grid gap-5">
      <div className="grid gap-5 sm:grid-cols-2">
        {fields.map(([name, label, autoComplete]) => (
          <div key={name} className="grid gap-2">
            <Label htmlFor={name}>{label}</Label>
            <Input
              id={name}
              autoComplete={autoComplete}
              aria-invalid={!!errors[name]}
              aria-describedby={errors[name] ? `${name}-error` : undefined}
              className="h-10"
              {...register(name)}
            />
            {errors[name] && (
              <p id={`${name}-error`} className="text-sm text-destructive">
                {errors[name]?.message}
              </p>
            )}
          </div>
        ))}
      </div>
      <div>
        <Button type="submit" disabled={!isDirty || update.isPending}>
          {update.isPending ? "Зберігаємо…" : "Зберегти зміни"}
        </Button>
      </div>
    </form>
  );
}
