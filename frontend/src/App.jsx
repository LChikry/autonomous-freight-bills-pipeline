import { useState, useEffect } from "react";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_URL;

function App() {
	const [activeTab, setActiveTab] = useState("hbl"); // 'hbl' or 'mbl'

	const [data, setData] = useState([]);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState(null);

	const [cursorHistory, setCursorHistory] = useState([null]);
	const [pageIndex, setPageIndex] = useState(0);
	const [nextCursor, setNextCursor] = useState(null);

	const [isProcessing, setIsProcessing] = useState(false);
	const [processStats, setProcessStats] = useState(null);

	useEffect(() => {
		setCursorHistory([null]);
		setPageIndex(0);
		setNextCursor(null);
		fetchDocuments(activeTab, null);
	}, [activeTab]);

	const fetchDocuments = async (type, cursor) => {
		setLoading(true);
		setError(null);
		try {
			let url = `${API_BASE}/${type}`;
			if (cursor) url += `?cursor=${cursor}`;

			const res = await fetch(url);
			if (!res.ok) throw new Error("Failed to fetch data");

			const json = await res.json();
			setData(json.documents);
			setNextCursor(json.next_cursor);
		} catch (err) {
			console.error(err);
			setError(err.message);
		} finally {
			setLoading(false);
		}
	};

	const handleProcess = async () => {
		setIsProcessing(true);
		setProcessStats(null);
		try {
			const res = await fetch(`${API_BASE}/ops/process`, {
				method: "POST",
			});
			if (!res.ok) throw new Error("Processing failed");
			const json = await res.json();

			// 2. Save the full summary statistics
			setProcessStats(json);

			// Refresh list to show new items
			fetchDocuments(activeTab, cursorHistory[pageIndex]);
		} catch (err) {
			alert("Error processing emails: " + err.message);
		} finally {
			setIsProcessing(false);
		}
	};

	const handleNext = () => {
		if (!nextCursor) return;
		const newHistory = [...cursorHistory, nextCursor];
		setCursorHistory(newHistory);
		setPageIndex(pageIndex + 1);
		fetchDocuments(activeTab, nextCursor);
	};

	const handlePrev = () => {
		if (pageIndex === 0) return;
		const prevIndex = pageIndex - 1;
		const prevCursor = cursorHistory[prevIndex];
		setPageIndex(prevIndex);
		fetchDocuments(activeTab, prevCursor);
	};

	return (
		<div className="container">
			<header className="header">
				<h1>BofL Analyzer</h1>
				<div className="actions">
					<button
						className="btn-primary"
						onClick={handleProcess}
						disabled={isProcessing}
					>
						{isProcessing ? "Processing..." : "Process Emails"}
					</button>
				</div>
			</header>

			{/* 3. Display the full Process Summary if available */}
			{processStats && (
				<div className="summary-box">
					<h3>Processing Complete</h3>
					<div className="stats-grid">
						<div className="stat-item">
							<span>Emails Scanned</span>
							<strong>
								{processStats.emails_processed_count}
							</strong>
						</div>
						<div className="stat-item">
							<span>Attachments</span>
							<strong>
								{processStats.attachments_processed_count}
							</strong>
						</div>
						<div className="stat-item">
							<span>BLs Found</span>
							<strong>{processStats.bl_processed_count}</strong>
						</div>
						<div className="stat-item success">
							<span>Created</span>
							<strong>{processStats.docs_created_count}</strong>
						</div>
						<div className="stat-item warning">
							<span>Duplicates Skipped</span>
							<strong>
								{processStats.skipped_duplicated_docs_count}
							</strong>
						</div>
					</div>
					<button
						className="close-stats"
						onClick={() => setProcessStats(null)}
					>
						Dismiss
					</button>
				</div>
			)}

			<div className="tabs">
				<button
					className={activeTab === "hbl" ? "tab active" : "tab"}
					onClick={() => setActiveTab("hbl")}
				>
					House Bills (HBL)
				</button>
				<button
					className={activeTab === "mbl" ? "tab active" : "tab"}
					onClick={() => setActiveTab("mbl")}
				>
					Master Bills (MBL)
				</button>
			</div>

			<div className="table-container">
				{error && <div className="error">Error: {error}</div>}

				{loading ? (
					<div className="loading">Loading records...</div>
				) : (
					<table className="data-table">
						<thead>
							<tr>
								<th>BL Number</th>
								<th>Type</th>
								<th>Status</th>
								<th>Parties</th>
								<th>Route</th>
								<th>Dates</th>
								<th>Email Subject</th>
								<th>Received</th>
								<th>Attachment</th>
							</tr>
						</thead>
						<tbody>
							{data.length === 0 ? (
								<tr>
									<td
										colSpan="9"
										style={{ textAlign: "center" }}
									>
										No records found
									</td>
								</tr>
							) : (
								data.map((row) => (
									<tr key={row.doc_id || row.bl_number}>
										<td className="font-bold">
											{row.bl_number}
										</td>
										<td>
											<span
												className={`badge ${row.doc_type}`}
											>
												{row.doc_type.toUpperCase()}
											</span>
										</td>
										<td>{row.email_status}</td>
										<td>
											<div className="cell-sub">
												<strong>S:</strong>{" "}
												{row.shipper_name}
												<br />
												<strong>C:</strong>{" "}
												{row.consignee_name}
											</div>
										</td>
										<td>
											<div className="cell-sub">
												<strong>POL:</strong>{" "}
												{row.port_of_loading}
												<br />
												<strong>POD:</strong>{" "}
												{row.port_of_discharge}
											</div>
										</td>
										<td>
											<div className="cell-sub">
												{row.etd && (
													<div>
														<strong>ETD:</strong>{" "}
														{row.etd}
													</div>
												)}
												{row.eta && (
													<div>
														<strong>ETA:</strong>{" "}
														{row.eta}
													</div>
												)}
											</div>
										</td>
										<td
											className="truncate"
											title={row.email.subject}
										>
											{row.email.subject}
										</td>
										<td className="whitespace-nowrap">
											{new Date(
												row.email.received_at,
											).toLocaleDateString()}
										</td>
										<td
											className="truncate"
											title={row.attachment.filename}
										>
											{row.attachment.filename}
										</td>
									</tr>
								))
							)}
						</tbody>
					</table>
				)}
			</div>

			<div className="pagination">
				<button
					onClick={handlePrev}
					disabled={pageIndex === 0 || loading}
				>
					&larr; Previous
				</button>
				<span>Page {pageIndex + 1}</span>
				<button onClick={handleNext} disabled={!nextCursor || loading}>
					Next &rarr;
				</button>
			</div>
		</div>
	);
}

export default App;
