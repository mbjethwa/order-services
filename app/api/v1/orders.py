import logging
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
import requests
from sqlalchemy import asc, desc, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette import status
from app.core.security import check_permissions
from app.db.base import get_db
from app.schemas.order_header import (
    OrderHeaderCreateRequest,
    OrderHeaderReadRequest,
)

from app.db.models.order_header import OrderHeader
from app.db.models.order_line import OrderLine
from app.core.config import settings


db_dependency = Annotated[Session, Depends(get_db)]

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_permissions((["manage_orders_ORDER_SERVICE"])))],
)
def create_order(
    db: db_dependency, order_request: OrderHeaderCreateRequest, request: Request
):
    """
    Processes a checkout order by validating the employee, department, and items,
    and then creating the order and associated checkout items in the database.
    Args:

        order_request (OrderHeaderCreateRequest): The request object containing
            the details of the checkout order
            # Example Order:
            # {
            #    "user_id": 123,
            #    "total_items": 2,
            #    "order_lines": [
            #        {
            #            "item_id": 456,
            #            "quantity": 2
            #        },
            #        {
            #            "item_id": 789,
            #            "quantity": 1
            #        }
            #    ]
            # }

    Raises:

        HTTPException:
        - If the employee, department, or any item is not found, or if an item
            does not have enough quantity in stock.
        - If there is an integrity error during the database order.
        - If there is a general database error during the order.
        - If there is an unexpected error during the order.
    Returns:

        dict: A dictionary containing a success message and the order details, including
            the order ID and creation timestamp.
    """

    try:
        # IMPORTANT NOTE: for simplicity, we are not validating the order details like user, items, etc.
        # In a more enhanced version, you would want to validate the user and items before creating the order.
        # For example, you might want to check if the user exists and if the items are valid.
        # You can also check if the items are in stock and reserve some quantity for the order.
        # Another approach is to have the validation between services handled by the frontend or a consumer service that validating the order with INVENTORY-SERVICE or AUTH-SERVICE before calling ORDER-SERVICE.

        # Create the checkout order
        new_order = OrderHeader(
            user_id=order_request.user_id,
            total_items=len(order_request.order_lines),
        )
        db.add(new_order)
        db.flush()  # Writes to the database to generate `order_id` but doesn't commit
        # print("new_order.order_id ", new_order.order_id)
        # Create the checkout items
        for index, item in enumerate(order_request.order_lines):
            # print("OrderLine ", item)
            order_line = OrderLine(
                order_id=new_order.order_id,
                line_number=index + 1,
                item_id=item.item_id,
                quantity=item.quantity,
            )
            db.add(order_line)
            # Access the token from the request header
            # print(
            #     "request.headers.get('Authorization') ",
            #     request.headers.get("Authorization"),
            # )
            print(
                f"Calling INVENTORY-SERVICE at {settings.INVENTORY_SERVICE_BASE_URL}/items/{item.item_id}?change_quantity={item.quantity}"
            )
            response = requests.patch(
                f"{settings.INVENTORY_SERVICE_BASE_URL}/items/{item.item_id}?change_quantity={item.quantity}",
                headers={"Authorization": request.headers.get("Authorization")},
            )
            if response.status_code != 200:
                # Rollback the transaction if the item update fails
                db.rollback()
                raise HTTPException(
                    status_code=400, detail="Failed to update item quantity"
                )

        # Commit the order and all lines
        db.commit()

        # print("Did go here!!!!")
        # The order is committed, so we can now fetch the order and checkout items
        stmt = select(OrderHeader).where(OrderHeader.order_id == new_order.order_id)
        order_header_result = db.execute(stmt).scalars().first()
        if order_header_result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch the committed order.",
            )

        return {
            "message": "Order created successfully",
            "order": order_header_result.order_id,
        }

    except IntegrityError as e:
        logging.error(f"Integrity error occurred: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.orig))
    except SQLAlchemyError as e:
        logging.error(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the checkout.",
        )
    except HTTPException as e:
        logging.error(f"HTTPException: {str(e)}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail,
        )
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the checkout.",
        )


@router.get(
    "/",
    response_model=list[OrderHeaderReadRequest],
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(
            check_permissions(
                ["manage_orders_ORDER_SERVICE", "view_orders_ORDER_SERVICE"]
            )
        )
    ],
)
def read_all_orders(
    db: db_dependency,
    limit: Optional[int] = Query(None, description="Number of records to return"),
    order_by: Optional[str] = Query(None, description="Order by column"),
    ascending: Optional[bool] = Query(True, description="Sort in ascending order"),
):
    """
    Fetch all orders from the database along with their associated permissions.

    Args:

        limit (int, optional): The number of records to return. Defaults to None.
        order_by (str, optional): The column to order the results by. Defaults to order_id.
        ascending (bool, optional): Sort in ascending order. Defaults to True.
        Note: the allowed columns are "order_id", "total_items", and "created_at".
    Returns:

        list[OrderHeader]: A list of OrderHeader objects with their associated items.
    Raises:

        HTTPException: If an integrity error or any other database error occurs,
                       an HTTPException is raised with an appropriate status code
                       and error message.
    """
    try:
        allowed_columns = [
            "order_id",
            "total_items",
            "created_at",
        ]  # Add valid column names here

        # Start building the query
        stmt = select(OrderHeader)

        # Apply ordering
        # Validate and set the order_by column or a default value
        if order_by is None:
            order_by = "order_id"
        order_by = (
            order_by.lower() if order_by.lower() in allowed_columns else "order_id"
        )
        order_column = getattr(OrderHeader, order_by)
        if order_column:
            if ascending:
                stmt = stmt.order_by(asc(order_column))
            else:
                stmt = stmt.order_by(desc(order_column))

        # Apply limit
        if limit is not None:
            stmt = stmt.limit(limit)

        # Execute the query
        return db.execute(stmt).scalars().all()

    except IntegrityError as e:
        logging.error(f"Integrity error occurred: {str(e.orig)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.orig))
    except SQLAlchemyError as e:
        logging.error(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching all orders.",
        )
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching all orders.",
        )


@router.get(
    "/{order_id}",
    response_model=OrderHeaderReadRequest,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(
            check_permissions(
                ["manage_orders_ORDER_SERVICE", "view_orders_ORDER_SERVICE"]
            )
        )
    ],
)
def read_order(db: db_dependency, order_id: int = Path(gt=0)):
    """
    Fetch a order by its ID from the database.
    Args:

        order_id (int): The ID of the order to fetch. Must be greater than 0.
    Returns:

        OrderHeader: The order object if found.
    Raises:

        HTTPException: If the order is not found, or if there is an integrity error,
                       database error, or any other unexpected error.
    """

    try:
        stmt = select(OrderHeader).where(OrderHeader.order_id == order_id)
        order_model = db.execute(stmt).scalars().first()

        if order_model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"order with id {order_id} not found.",
            )

        return order_model

    except IntegrityError as e:
        logging.error(f"Integrity error occurred: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.orig))
    except SQLAlchemyError as e:
        logging.error(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching the order with id {order_id}.",
        )
    except HTTPException as e:
        logging.error(f"HTTPException: {str(e)}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail,
        )
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching the order with id {order_id}.",
        )
