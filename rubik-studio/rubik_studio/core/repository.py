from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from rubik_studio.core.audit_logger import audit
from rubik_studio.core.database import get_session_factory
from rubik_studio.core.models import Object, ObjectLink, ObjectType
from rubik_studio.core.validators import validate_description, validate_link, validate_object_name


class RepositoryError(Exception):
    """Ошибка валидации или бизнес-логики репозитория. Сообщение — человекочитаемое."""


class RepositoryService:
    # ── Типы объектов ────────────────────────────────────────────────────

    async def list_types(self) -> list[ObjectType]:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(select(ObjectType).order_by(ObjectType.name))
            return list(result.scalars().all())

    async def get_type(self, type_id: str) -> ObjectType | None:
        factory = get_session_factory()
        async with factory() as session:
            return await session.get(ObjectType, type_id)

    # ── Объекты ──────────────────────────────────────────────────────────

    async def list_objects(
        self, type_id: str | None = None, search: str | None = None
    ) -> list[Object]:
        factory = get_session_factory()
        async with factory() as session:
            query = select(Object).options(selectinload(Object.type))
            if type_id:
                query = query.where(Object.type_id == type_id)
            if search:
                query = query.where(Object.name.ilike(f"%{search}%"))
            query = query.order_by(Object.name)
            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_object(self, object_id: str) -> Object | None:
        factory = get_session_factory()
        async with factory() as session:
            query = select(Object).options(selectinload(Object.type)).where(Object.id == object_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def create_object(
        self,
        type_id: str,
        name: str,
        description: str = "",
        attributes: dict[str, Any] | None = None,
        username: str = "local",
        user_id: str | None = None,
    ) -> Object:
        is_valid, message = validate_object_name(name)
        if not is_valid:
            raise RepositoryError(message)
        is_valid, message = validate_description(description)
        if not is_valid:
            raise RepositoryError(message)
        if not type_id:
            raise RepositoryError("Выберите тип объекта")

        factory = get_session_factory()
        async with factory() as session:
            obj_type = await session.get(ObjectType, type_id)
            if obj_type is None:
                raise RepositoryError("Выберите тип объекта")

            duplicate = await session.execute(
                select(Object).where(Object.type_id == type_id, Object.name == name.strip())
            )
            if duplicate.scalar_one_or_none() is not None:
                raise RepositoryError(
                    f'Объект типа "{obj_type.name}" с названием "{name.strip()}" уже существует'
                )

            new_object = Object(
                type_id=type_id,
                name=name.strip(),
                description=description or "",
                attributes=attributes or {},
            )
            session.add(new_object)
            await session.commit()
            await session.refresh(new_object, attribute_names=["id", "name"])

        await audit.log(
            action="CREATE",
            entity_type="Object",
            entity_id=new_object.id,
            entity_name=new_object.name,
            user_id=user_id,
            username=username,
        )
        return new_object

    async def update_object(
        self,
        object_id: str,
        name: str | None = None,
        description: str | None = None,
        attributes: dict[str, Any] | None = None,
        username: str = "local",
        user_id: str | None = None,
    ) -> Object:
        factory = get_session_factory()
        async with factory() as session:
            obj = await session.get(Object, object_id)
            if obj is None:
                raise RepositoryError("Объект не найден. Возможно, он был удалён")

            if name is not None:
                is_valid, message = validate_object_name(name)
                if not is_valid:
                    raise RepositoryError(message)
                obj.name = name.strip()

            if description is not None:
                is_valid, message = validate_description(description)
                if not is_valid:
                    raise RepositoryError(message)
                obj.description = description

            if attributes is not None:
                obj.attributes = attributes

            await session.commit()
            result_name = obj.name
            result_id = obj.id

        await audit.log(
            action="UPDATE",
            entity_type="Object",
            entity_id=result_id,
            entity_name=result_name,
            user_id=user_id,
            username=username,
        )
        return await self.get_object(object_id)  # type: ignore[return-value]

    async def delete_object(
        self, object_id: str, username: str = "local", user_id: str | None = None
    ) -> None:
        factory = get_session_factory()
        async with factory() as session:
            obj = await session.get(Object, object_id)
            if obj is None:
                raise RepositoryError("Объект не найден. Возможно, он уже удалён")
            name = obj.name
            await session.delete(obj)
            await session.commit()

        await audit.log(
            action="DELETE",
            entity_type="Object",
            entity_id=object_id,
            entity_name=name,
            user_id=user_id,
            username=username,
        )

    async def count_usages(self, object_id: str) -> dict[str, int]:
        """Подсчёт использования объекта (для предупреждения перед удалением)."""
        factory = get_session_factory()
        async with factory() as session:
            links_result = await session.execute(
                select(ObjectLink).where(
                    (ObjectLink.source_id == object_id) | (ObjectLink.target_id == object_id)
                )
            )
            links_count = len(links_result.scalars().all())

            bindings_count = 0
            try:
                from rubik_studio.core.models import ModelElementBinding

                bindings_result = await session.execute(
                    select(ModelElementBinding).where(ModelElementBinding.object_id == object_id)
                )
                bindings_count = len(bindings_result.scalars().all())
            except Exception:  # noqa: BLE001
                pass

            return {"links": links_count, "models": bindings_count}

    # ── Связи ────────────────────────────────────────────────────────────

    async def list_links(self, object_id: str | None = None) -> list[ObjectLink]:
        factory = get_session_factory()
        async with factory() as session:
            query = select(ObjectLink)
            if object_id:
                query = query.where(
                    (ObjectLink.source_id == object_id) | (ObjectLink.target_id == object_id)
                )
            result = await session.execute(query)
            return list(result.scalars().all())

    async def create_link(
        self,
        source_id: str,
        target_id: str,
        link_type: str,
        attributes: dict[str, Any] | None = None,
        username: str = "local",
        user_id: str | None = None,
    ) -> ObjectLink:
        is_valid, message = validate_link(source_id, target_id)
        if not is_valid:
            raise RepositoryError(message)

        factory = get_session_factory()
        async with factory() as session:
            src = await session.get(Object, source_id)
            tgt = await session.get(Object, target_id)
            if src is None or tgt is None:
                raise RepositoryError("Один из объектов не найден")

            duplicate = await session.execute(
                select(ObjectLink).where(
                    ObjectLink.source_id == source_id,
                    ObjectLink.target_id == target_id,
                    ObjectLink.link_type == link_type,
                )
            )
            if duplicate.scalar_one_or_none() is not None:
                raise RepositoryError("Такая связь уже существует")

            link = ObjectLink(
                source_id=source_id,
                target_id=target_id,
                link_type=link_type,
                attributes=attributes or {},
            )
            session.add(link)
            await session.commit()
            await session.refresh(link)
            src_name, tgt_name = src.name, tgt.name

        await audit.log(
            action="CREATE_LINK",
            entity_type="ObjectLink",
            entity_id=link.id,
            entity_name=f"{src_name} → {tgt_name} ({link_type})",
            user_id=user_id,
            username=username,
        )
        return link

    async def delete_link(
        self, link_id: str, username: str = "local", user_id: str | None = None
    ) -> None:
        factory = get_session_factory()
        async with factory() as session:
            link = await session.get(ObjectLink, link_id)
            if link is None:
                raise RepositoryError("Связь не найдена. Возможно, она уже удалена")
            await session.delete(link)
            await session.commit()

        await audit.log(
            action="DELETE_LINK",
            entity_type="ObjectLink",
            entity_id=link_id,
            username=username,
            user_id=user_id,
        )


repo_service = RepositoryService()
