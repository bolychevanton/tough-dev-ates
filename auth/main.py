from fastapi import FastAPI, Depends, HTTPException
from common.authorizer import Authorizer
from auth.schema import RegisterDetails, LoginDetails
from auth.authenticator import Authentificator
from auth.password import get_password_hash, verify_password
from auth.config import public_key, private_key, expire, algorithm, db_url, nats_url
from auth import dbmodel
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio.engine import create_async_engine
import nats
from nats.js import JetStreamContext
import orjson
from contextlib import asynccontextmanager
import uuid
from datetime import datetime

auhtentificator = Authentificator(key=private_key, algorithm=algorithm, expire=expire)
authorizer = Authorizer(key=public_key, algorithm=algorithm)
jetstream: JetStreamContext = None
engine = create_async_engine(db_url)


@asynccontextmanager
async def instantiate_db_and_broker(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(dbmodel.SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        if (
            await session.exec(
                select(dbmodel.Account).where(
                    col(dbmodel.Account.email) == "root@localhost.ru"
                )
            )
        ).first() is None:
            session.add(
                dbmodel.Account(
                    fullname="root",
                    email="root@localhost.ru",
                    role="admin",
                    public_id=str(uuid.uuid4()),
                    password_hash=get_password_hash("root"),
                )
            )
            await session.commit()

    nc = await nats.connect(nats_url)
    global jetstream
    jetstream = nc.jetstream()

    # "auth.account" for auth business events
    # "account.streams" for cud events
    await jetstream.add_stream(
        name="auth", subjects=["ACCOUNTS.*", "ACCOUNTS-STREAMS.*"]
    )
    yield
    await nc.close()


app = FastAPI(lifespan=instantiate_db_and_broker)


@app.post("/register", status_code=201)
async def register(register_details: RegisterDetails):
    async with AsyncSession(engine, expire_on_commit=False) as session:
        account_with_email = (
            await session.exec(
                select(dbmodel.Account).where(
                    col(dbmodel.Account.email) == register_details.email
                )
            )
        ).first()
        if account_with_email is not None:
            raise HTTPException(status_code=400, detail="Email is taken")

    async with AsyncSession(engine, expire_on_commit=False) as session:
        new_account = dbmodel.Account(
            fullname=register_details.fullname,
            email=register_details.email,
            role="worker",
            public_id=str(uuid.uuid4()),
            password_hash=get_password_hash(register_details.password),
        )
        session.add(new_account)
        await session.commit()
        event_data = orjson.dumps(
            dict(
                public_id=new_account.public_id,
                fullname=new_account.fullname,
                email=new_account.email,
                role=new_account.role,
                created_at=new_account.created_at,
            )
        )
    await jetstream.publish(
        subject="ACCOUNTS-STREAMS.AccountCreated", payload=event_data
    )  # cud

    # Maybe not reasonable to publish BE here, but just in case
    await jetstream.publish(subject="ACCOUNTS.AccountCreated", payload=event_data)  # be
    return {"message": "Account created"}


@app.post("/login")
async def login(login_details: LoginDetails):
    async with AsyncSession(engine, expire_on_commit=False) as session:
        account_with_email = (
            await session.exec(
                select(dbmodel.Account).where(
                    col(dbmodel.Account.email) == login_details.email
                )
            )
        ).first()

    if (account_with_email is None) or (
        not verify_password(login_details.password, account_with_email.password_hash)
    ):
        raise HTTPException(status_code=401, detail="Invalid email and/or password")
    token = auhtentificator.encode_token(
        account_with_email.public_id, account_with_email.role
    )

    await jetstream.publish(
        subject="ACCOUNTS-STREAMS.AccountLogined",
        payload=orjson.dumps(
            dict(
                public_id=account_with_email.public_id,
                email=account_with_email.email,
                logined_at=datetime.now(),
            )
        ),
    )  # cud

    return {"token": token}


@app.post(
    "/change_role",
    status_code=200,
    dependencies=[Depends(authorizer.restrict_access(to=["admin", "manager"]))],
)
async def change_role(
    new_role: str, public_user_id: str | None = None, email: str | None = None
):
    if (public_user_id is None) + (email is None) != 1:
        raise HTTPException(
            status_code=400, detail="Provide either public_user_id or email"
        )

    statement = (
        select(dbmodel.Account).where(col(dbmodel.Account.public_id) == public_user_id)
        if public_user_id is not None
        else select(dbmodel.Account).where(col(dbmodel.Account.email) == email)
    )

    async with AsyncSession(engine, expire_on_commit=False) as session:
        account = (await session.exec(statement)).first()
        if account is None:
            raise HTTPException(status_code=404, detail="Account not found")
        account.role = new_role
        account.updated_at = datetime.now()
        session.add(account)
        session.commit()
        event_data = orjson.dumps(
            dict(
                public_id=account.public_id,
                fullname=account.fullname,
                email=account.email,
                role=account.role,
                updated_at=account.updated_at,
            )
        )

    await jetstream.publish(
        subject="ACCOUNTS-STREAMS.RoleChanged", payload=event_data
    )  # cud
    await jetstream.publish(subject="ACCOUNTS.RoleChanged", payload=event_data)  # be
    return {"status": "success"}


# with TestClient(app) as client:
#     client.get(headers={"Authorization": f"Bearer {jwt_encoder.encode_token('test')}"})
