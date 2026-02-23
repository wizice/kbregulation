# -*- coding: utf-8 -*-
"""
    timescaledb
    ~~~~~~~~~~~~~~~~~~~~~~~~

    TimescaleDB connection and query with logging

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""

#--- timescale_dbv1.py
#----------------------------------------
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime

class TimescaleDB:
    def __init__(self, database="wzdb", user='wzuser', password='wzuserpwd!', host="127.0.0.1", port=5432, 
                 logger=None, log_level=logging.INFO):
        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = port
        self.stmt = None
        self.data = None
        self.error = None
        
        # Logger 설정
        if logger:
            self.Log = logger
            self.Log.info("logger 받음")
        else:
            # 기본 logger 생성
            self.Log = logging.getLogger(f'TimescaleDB.{database}')
            #self.Log.info("logger 새로 생성")
            #self.Log.setLevel(log_level)
            self.Log.setLevel(logging.DEBUG)
            
            # 핸들러가 없으면 추가
            if not self.Log.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                handler.setFormatter(formatter)
                self.Log.addHandler(handler)
        
        try:
            self.pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                user=user,
                password=password,
                host=host,
                port=port,
                database=database
            )
            self.con = None
            self.Log.info(f"Connection pool created for database: {database} at {host}:{port}")
        except Exception as e:
            self.Log.error(f"Failed to create connection pool: {e}")
            raise

    def connect(self):
        try:
            self.con = self.pool.getconn()
            self.Log.debug("Successfully acquired a connection from pool")
            return self.con
        except Exception as e:
            self.Log.error(f"Failed to acquire connection: {e}")
            self.con = None
            raise

    def close(self):
        if self.con is None:
            self.Log.debug("Connection was never initialized. Skipping close.")
            return
            
        if self.con:
            try:
                self.pool.putconn(self.con)
                self.con = None
                self.Log.debug("Successfully returned connection to pool")
            except psycopg2.pool.PoolError as e:
                self.Log.error(f"Failed to return connection to pool: {e}")
        else:
            self.Log.debug("No connection to close.")

    def commit(self):
        if self.con:
            self.con.commit()
            self.Log.debug("Transaction committed")
        else:
            self.Log.warning("No connection available for commit")

    def rollback(self):
        if self.con:
            self.con.rollback()
            self.Log.info("Transaction rolled back")
        else:
            self.Log.warning("No connection available for rollback")

    def cur_query(self, stmt, data=(), one=False, commit=False):
        self.error = ""
        self.stmt = stmt
        self.data = data
        con = self.con
        if not con:
            con = self.pool.getconn()
            self.Log.debug("Acquired new connection for cur_query")
        return self.query(stmt, data, one, commit, con)

    def query(self, stmt, data=(), one=False, commit=False, con=None):
        self.error = ""
        self.stmt = stmt
        self.data = data
        usecon = False
        start_time = datetime.now()
        
        if con:
            usecon = True
        if not con:
            con = self.pool.getconn()
            self.Log.debug("Acquired new connection from pool")

        if not con:
            self.error = "Connection failed"
            self.Log.error(self.error)
            return None

        try:
            with con.cursor(cursor_factory=RealDictCursor) as cur:
                #self.Log.debug(f"Executing query: {stmt[:100]}{'...' if len(stmt) > 100 else ''}")
                self.Log.debug(f"Executing query: {stmt}")
                if data:
                    self.Log.debug(f"Query parameters: {data}")
                    
                cur.execute(stmt, data)
                
                # 쿼리 실행 시간 로깅
                execution_time = (datetime.now() - start_time).total_seconds()
                self.Log.debug(f"Query executed in {execution_time:.3f} seconds")

                if commit:
                    con.commit()
                    self.Log.debug("Changes committed")

                if stmt.strip().upper().startswith("SELECT"):
                    result = cur.fetchall()
                    self.Log.debug(f"SELECT returned {len(result) if result else 0} rows")
                    #if result:
                    #    self.Log.debug(f"SELECT result sample:{result[0]}")
                    return result[0] if one and result else result
                elif stmt.strip().upper().startswith("WITH") and  cur.description:
                    result = cur.fetchall()
                    self.Log.debug(f"SELECT returned {len(result) if result else 0} rows")
                    #if result:
                    #    self.Log.debug(f"SELECT result sample:{result[0]}")
                    return result[0] if one and result else result
                    
                elif stmt.strip().upper().startswith("INSERT"):
                    if stmt.strip().upper().find("RETURNING") >= 0:
                        result = cur.fetchall()
                        row = result[0] if result else {}
                        if len(row.keys()) == 1:
                            value = list(row.values())[0]
                            self.Log.debug(f"INSERT returned: {value}")
                            return value
                        else:
                            values = ",".join([str(v) for v in list(row.values())])
                            self.Log.debug(f"INSERT returned multiple values: {values}")
                            return values
                    self.Log.debug(f"INSERT affected {cur.rowcount} rows")
                    return cur.lastrowid
                    
                elif stmt.strip().upper().startswith("UPDATE"):
                    if stmt.strip().upper().find("RETURNING") >= 0:
                        result = cur.fetchall()
                        row = result[0] if result else {}
                        if len(row.keys()) == 1:
                            value = list(row.values())[0]
                            self.Log.debug(f"UPDATE returned: {value}")
                            return value
                        else:
                            values = ",".join([str(v) for v in list(row.values())])
                            self.Log.debug(f"UPDATE returned multiple values: {values}")
                            return values
                    self.Log.debug(f"UPDATE affected {cur.rowcount} rows")
                    return cur.rowcount
                    
                elif stmt.strip().upper().startswith("DELETE"):
                    self.Log.debug(f"DELETE affected {cur.rowcount} rows")
                    return cur.rowcount
                    
        except Exception as e:
            self.error = str(e)
            self.Log.error(f"Query execution failed: {self.error}")
            self.Log.error(f"Failed query: {stmt}")
            self.Log.error(f"Query data: {data}")
            if commit:
                con.rollback()
                self.Log.info("Transaction rolled back due to error")
            raise
        finally:
            if not usecon:
                self.pool.putconn(con)
                self.Log.debug("Connection returned to pool")

        return None

    def insert(self, table, data, return_key="", one=True, usecon=False):
        cols = ', '.join(data.keys())
        vals = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table} ({cols}) VALUES ({vals})"
        if return_key:
            query += f" RETURNING {return_key}"
        query += ";"
        
        self.Log.info(f"Inserting into {table}: {list(data.keys())}")
        
        if usecon:
            return self.cur_query(query, tuple(data.values()), one=one, commit=True)
        return self.query(query, tuple(data.values()), one=one, commit=True)

    def update(self, table, data, condition, return_key="", one=True, usecon=False):
        set_clause = ', '.join([f"{col} = %s" for col in data.keys()])
        cond_clause = ' AND '.join([f"{col} = %s" for col in condition.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {cond_clause}"
        if return_key:
            query += f" RETURNING {return_key}"
        query += ";"
        
        self.Log.info(f"Updating {table}: SET {list(data.keys())} WHERE {list(condition.keys())}")
        
        if usecon:
            return self.cur_query(query, tuple(data.values()) + tuple(condition.values()), one=one, commit=True)
        return self.query(query, tuple(data.values()) + tuple(condition.values()), one=one, commit=True)

    def delete(self, table, condition, one=True, usecon=False):
        cond_clause = ' AND '.join([f"{col} = %s" for col in condition.keys()])
        query = f"DELETE FROM {table} WHERE {cond_clause};"
        
        self.Log.info(f"Deleting from {table} WHERE {list(condition.keys())}")
        
        if usecon:
            return self.cur_query(query, tuple(condition.values()), one=one, commit=True)
        return self.query(query, tuple(condition.values()), one=one, commit=True)

    def select(self, table, columns='*', condition=None, one=False, usecon=False, order_by=None, limit=None):
        cond_clause = ''
        params = ()
        if condition:
            cond_clause = ' WHERE ' + ' AND '.join([f"{col} = %s" for col in condition.keys()])
            params = tuple(condition.values())
            
        query = f"SELECT {columns} FROM {table}{cond_clause}"
        
        if order_by:
            query += f" ORDER BY {order_by}"
            
        if limit:
            query += f" LIMIT {limit}"
            
        query += ";"
        
        self.Log.info(f"Selecting from {table}: columns={columns}, condition={list(condition.keys()) if condition else 'None'}")
        
        if usecon:
            self.Log.debug(f"use cur_query")
            return self.cur_query(query, params, one=one)
        return self.query(query, params, one=one)

    def __del__(self):
        """소멸자: 연결 풀 정리"""
        try:
            if hasattr(self, 'pool') and self.pool:
                self.pool.closeall()
                self.Log.info("Connection pool closed")
        except Exception as e:
            if hasattr(self, 'Log'):
                self.Log.error(f"Error closing connection pool: {e}")


# Example Usage
if __name__ == "__main__":
    # Logger 설정
    logging.basicConfig(level=logging.DEBUG)
    
    db = TimescaleDB(
        database="your_db", 
        user="your_user", 
        password="your_password", 
        host="127.0.0.1", 
        port=5432,
        log_level=logging.DEBUG
    )

    try:
        # Insert example
        inserted_id = db.insert("monitor", {
            "account_seq": 1,
            "device_seq": 101,
            "dg": 50.25,
            "dn": 30.75
        }, return_key="id")
        print(f"Inserted ID: {inserted_id}")

        # Update example
        updated_rows = db.update("monitor", {"dg": 55.0}, {"account_seq": 1, "device_seq": 101})
        print(f"Updated Rows: {updated_rows}")

        # Select example
        rows = db.select("monitor", "account_seq, device_seq, dg, dn", {"account_seq": 1})
        print(f"Selected Rows: {rows}")

        # Delete example
        deleted_rows = db.delete("monitor", {"account_seq": 1, "device_seq": 101})
        print(f"Deleted Rows: {deleted_rows}")
        
    except Exception as e:
        db.Log.error(f"Example failed: {e}")
    finally:
        db.close()
